"""
Módulo de renderização 3D com ModernGL para integração com Pygame.
Suporta carregamento de modelos .glb e renderização com fog.
"""
import moderngl
import numpy as np
import glm
import struct
from pygltflib import GLTF2
import pygame
import os
import math


class Renderer3D:
    """Renderizador 3D usando ModernGL integrado com Pygame."""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ctx = None
        self.initialized = False
        self.models = {}
        self.fbo = None
        self.texture = None
        self.textures = {}
        self.last_error = None
        
        # Câmera
        self.cam_pos = glm.vec3(0, 0, 5)
        self.cam_target = glm.vec3(0, 0, 0)
        self.cam_up = glm.vec3(0, 1, 0)
        
        # Fog
        self.fog_color = glm.vec3(0.8, 0.85, 0.9)
        self.fog_density = 0.0
        self.fog_start = 1.0
        self.fog_end = 50.0
        
        self._init_context()
    
    def _init_context(self):
        """Inicializa contexto OpenGL standalone."""
        errors = []
        ctx = None
        for backend in (None, "wgl", "egl", "osmesa"):
            try:
                if backend is None:
                    ctx = moderngl.create_standalone_context()
                else:
                    ctx = moderngl.create_standalone_context(backend=backend)
                break
            except Exception as e:
                errors.append((backend or "auto", str(e)))
                ctx = None
        if ctx is None:
            msg = " | ".join([f"{b}:{m}" for b, m in errors]) if errors else "Falha desconhecida"
            self.last_error = msg[:500]
            print(f"[Renderer3D] Falha ao inicializar: {self.last_error}")
            self.initialized = False
            return

        self.ctx = ctx
        self.last_error = None
        try:
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.CULL_FACE)

            self.texture = self.ctx.texture((self.width, self.height), 4)
            depth = self.ctx.depth_renderbuffer((self.width, self.height))
            self.fbo = self.ctx.framebuffer(color_attachments=[self.texture], depth_attachment=depth)

            self._create_shaders()
            self.initialized = True
        except Exception as e:
            self.last_error = str(e)[:500]
            print(f"[Renderer3D] Falha ao finalizar init: {self.last_error}")
            self.initialized = False
    
    def _create_shaders(self):
        """Cria shaders com suporte a fog."""
        vertex_shader = """
        #version 330
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        in vec3 in_position;
        in vec3 in_normal;
        in vec2 in_texcoord;
        
        out vec3 v_position;
        out vec3 v_normal;
        out vec2 v_texcoord;
        out float v_dist;
        
        void main() {
            vec4 world_pos = model * vec4(in_position, 1.0);
            vec4 view_pos = view * world_pos;
            gl_Position = projection * view_pos;
            
            v_position = world_pos.xyz;
            v_normal = mat3(model) * in_normal;
            v_texcoord = in_texcoord;
            v_dist = length(view_pos.xyz);
        }
        """
        
        fragment_shader = """
        #version 330
        
        uniform vec3 light_dir;
        uniform vec3 fog_color;
        uniform float fog_density;
        uniform float fog_start;
        uniform float fog_end;
        uniform vec3 base_color;
        uniform sampler2D tex;
        uniform bool use_texture;
        uniform float tex_scale;
        uniform int tex_mode; // 0=UV, 1=Triplanar, 2=Planar Top-Down
        uniform int debug_mode; // 0=Normal, 1=Fullbright (Tex only), 2=Normals
        
        in vec3 v_position;
        in vec3 v_normal;
        in vec2 v_texcoord;
        in float v_dist;
        
        out vec4 fragColor;
        
        void main() {
            vec3 norm = normalize(v_normal);
            
            // Debug: Normais
            if (debug_mode == 2) {
                fragColor = vec4(norm * 0.5 + 0.5, 1.0);
                return;
            }
            
            float diff = max(dot(norm, normalize(light_dir)), 0.0);
            float ambient = 0.6;
            float hemi = 0.3 * (0.5 + 0.5 * clamp(norm.y, 0.0, 1.0));
            float light = ambient + diff * 0.7 + hemi;
            
            vec3 color = base_color;
            if (use_texture) {
                if (tex_mode == 0) {
                    // UV Mapping
                    color = color * texture(tex, v_texcoord).rgb;
                } else if (tex_mode == 2) {
                    // Planar Top-Down (XZ plane)
                    // Usa tex_scale para ajustar tiling. 
                    // Se tex_scale for pequeno (ex: 1/tamanho_terreno), cobre tudo.
                    vec2 uv = v_position.xz * tex_scale;
                    
                    // Centraliza (opcional, assume origem no centro)
                    uv += 0.5; 
                    
                    color = color * texture(tex, uv).rgb;
                } else {
                    // Tri-planar Mapping
                    vec3 n = normalize(v_normal);
                    vec3 w = abs(n);
                    float sumw = w.x + w.y + w.z;
                    if (sumw < 0.001) {
                        w = vec3(0.33, 0.33, 0.34);
                    } else {
                        w = w / sumw;
                    }
                    vec2 uvx = v_position.yz * tex_scale;
                    vec2 uvy = v_position.xz * tex_scale;
                    vec2 uvz = v_position.xy * tex_scale;
                    uvx = fract(uvx);
                    uvy = fract(uvy);
                    uvz = fract(uvz);
                    vec3 cx = texture(tex, uvx).rgb;
                    vec3 cy = texture(tex, uvy).rgb;
                    vec3 cz = texture(tex, uvz).rgb;
                    vec3 tcol = cx * w.x + cy * w.y + cz * w.z;
                    color = color * tcol;
                }
            }
            
            // Debug: Fullbright (ignora luz e retorna cor direta)
            if (debug_mode == 1) {
                fragColor = vec4(color, 1.0);
                return;
            }
            
            color *= light;
            
            float fog_factor = 0.0;
            if (fog_density > 0.001) {
                fog_factor = 1.0 - exp(-fog_density * v_dist);
                fog_factor = clamp(fog_factor, 0.0, 1.0);
            }
            
            vec3 final_color = mix(color, fog_color, fog_factor);
            fragColor = vec4(final_color, 1.0);
        }
        """
        
        self.program = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
        
        # Uniforms padrão
        self.program['light_dir'].value = (0.5, 1.0, 0.3)
        self.program['fog_color'].value = tuple(self.fog_color)
        self.program['fog_density'].value = self.fog_density
        self.program['base_color'].value = (1.0, 1.0, 1.0)
        self.program['use_texture'].value = False
        self.program['tex_scale'].value = 0.02
        self.program['tex_mode'].value = 1
        self.program['debug_mode'].value = 0
        self._textures_enabled = True
        self.debug_mode_val = 0
    
    def set_debug_mode(self, mode):
        """Define modo de debug (0=Normal, 1=Fullbright, 2=Normals)."""
        self.debug_mode_val = mode
        if self.initialized:
            try:
                self.program['debug_mode'].value = mode
            except Exception:
                pass

    def load_glb(self, name, filepath, rotate_x_90=False):
        """Carrega modelo .glb e armazena com nome."""
        if not self.initialized:
            return False
        
        try:
            gltf = GLTF2().load(filepath)
            
            # Extrai dados binários
            binary_blob = gltf.binary_blob()
            if binary_blob is None:
                # Tenta carregar buffer externo
                buffer = gltf.buffers[0]
                buffer_path = os.path.join(os.path.dirname(filepath), buffer.uri)
                with open(buffer_path, 'rb') as f:
                    binary_blob = f.read()
            
            all_vertices = []
            all_indices = []
            total_vertex_count = 0
            
            for mesh in gltf.meshes:
                for primitive in mesh.primitives:
                    # Verifica modo de desenho (4 = TRIANGLES)
                    if primitive.mode is not None and primitive.mode != 4:
                        print(f"[Renderer3D] Aviso: Primitive mode {primitive.mode} não suportado totalmente (esperado 4). Resultado pode ser incorreto.")
                    
                    # Posições
                    pos_accessor = gltf.accessors[primitive.attributes.POSITION]
                    pos_view = gltf.bufferViews[pos_accessor.bufferView]
                    pos_data = binary_blob[pos_view.byteOffset:pos_view.byteOffset + pos_view.byteLength]
                    positions = np.frombuffer(pos_data, dtype=np.float32).reshape(-1, 3)
                    
                    # Normais
                    if primitive.attributes.NORMAL is not None:
                        norm_accessor = gltf.accessors[primitive.attributes.NORMAL]
                        norm_view = gltf.bufferViews[norm_accessor.bufferView]
                        norm_data = binary_blob[norm_view.byteOffset:norm_view.byteOffset + norm_view.byteLength]
                        normals = np.frombuffer(norm_data, dtype=np.float32).reshape(-1, 3)
                    else:
                        normals = np.zeros_like(positions)
                        normals[:, 1] = 1.0
                    
                    # UVs
                    if primitive.attributes.TEXCOORD_0 is not None:
                        uv_accessor = gltf.accessors[primitive.attributes.TEXCOORD_0]
                        uv_view = gltf.bufferViews[uv_accessor.bufferView]
                        uv_data = binary_blob[uv_view.byteOffset:uv_view.byteOffset + uv_view.byteLength]
                        uvs = np.frombuffer(uv_data, dtype=np.float32).reshape(-1, 2)
                    else:
                        uvs = np.zeros((len(positions), 2), dtype=np.float32)
                    
                    # Índices
                    if primitive.indices is not None:
                        idx_accessor = gltf.accessors[primitive.indices]
                        idx_view = gltf.bufferViews[idx_accessor.bufferView]
                        idx_data = binary_blob[idx_view.byteOffset:idx_view.byteOffset + idx_view.byteLength]
                        
                        if idx_accessor.componentType == 5123:  # UNSIGNED_SHORT
                            indices = np.frombuffer(idx_data, dtype=np.uint16).astype(np.uint32)
                        elif idx_accessor.componentType == 5125:  # UNSIGNED_INT
                            indices = np.frombuffer(idx_data, dtype=np.uint32).copy()
                        elif idx_accessor.componentType == 5121:  # UNSIGNED_BYTE
                            indices = np.frombuffer(idx_data, dtype=np.uint8).astype(np.uint32)
                        else:
                            indices = np.arange(len(positions), dtype=np.uint32)
                    else:
                        indices = np.arange(len(positions), dtype=np.uint32)
                    
                    # Ajusta índices para o offset global de vértices
                    indices += total_vertex_count
                    
                    # Combina dados de vértice
                    vertex_data = np.hstack([positions, normals, uvs]).astype(np.float32)
                    all_vertices.append(vertex_data)
                    all_indices.append(indices)
                    
                    total_vertex_count += len(positions)
            
            if not all_vertices:
                return False
            
            vertices = np.vstack(all_vertices)
            indices = np.concatenate(all_indices).astype(np.uint32)
            
            # Rotação opcional para corrigir eixo Z-up (comum em exports de Blender)
            if rotate_x_90:
                # Rotaciona -90 graus no eixo X
                # (x, y, z) -> (x, z, -y)
                # Posições
                y = vertices[:, 1].copy()
                z = vertices[:, 2].copy()
                vertices[:, 1] = z
                vertices[:, 2] = -y
                # Normais
                ny = vertices[:, 4].copy()
                nz = vertices[:, 5].copy()
                vertices[:, 4] = nz
                vertices[:, 5] = -ny
            
            try:
                mins = vertices[:,0:3].min(axis=0)
                maxs = vertices[:,0:3].max(axis=0)
                size = maxs - mins
                print(f"[Renderer3D] Bounds '{name}': min={tuple(mins)}, max={tuple(maxs)}, size={tuple(size)}")
            except Exception:
                pass
            
            vbo = self.ctx.buffer(vertices.tobytes())
            ibo = self.ctx.buffer(indices.tobytes())
            
            vao = self.ctx.vertex_array(
                self.program,
                [(vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
                index_buffer=ibo
            )
            
            self.models[name] = {
                'vao': vao,
                'vbo': vbo,
                'ibo': ibo,
                'vertex_count': len(indices),
                'position': glm.vec3(0, 0, 0),
                'rotation': glm.vec3(0, 0, 0),
                'scale': glm.vec3(1, 1, 1),
                'texture': None,
                'tex_scale': 0.02,
                'visible': True,
                'bounds_min': glm.vec3(*mins) if 'mins' in locals() else glm.vec3(0,0,0),
                'bounds_max': glm.vec3(*maxs) if 'maxs' in locals() else glm.vec3(0,0,0),
                'bounds_size': glm.vec3(*size) if 'size' in locals() else glm.vec3(1,1,1)
            }
            
            # Gera Heightmap simples para colisão (Grid 100x100)
            try:
                # bounds já calculados
                grid_size = 100
                min_x, min_z = mins[0], mins[2]
                max_x, max_z = maxs[0], maxs[2]
                step_x = (max_x - min_x) / grid_size
                step_z = (max_z - min_z) / grid_size
                
                # Inicializa com altura mínima
                heightmap = np.full((grid_size, grid_size), mins[1], dtype=np.float32)
                
                # Popula grid (amostragem simples: pega o ponto mais alto em cada célula)
                # Otimização: iterar apenas uma fração dos vértices se for muito pesado
                # Vértices format: [x, y, z, nx, ny, nz, u, v]
                pts = vertices[:, 0:3]
                
                # Vetorizado: Calcula índices
                idxs_x = ((pts[:, 0] - min_x) / step_x).astype(int)
                idxs_z = ((pts[:, 2] - min_z) / step_z).astype(int)
                
                # Clampa índices
                idxs_x = np.clip(idxs_x, 0, grid_size - 1)
                idxs_z = np.clip(idxs_z, 0, grid_size - 1)
                
                # Loop para preencher max (infelizmente numpy.maximum.at é necessário, mas vamos simplificar)
                # Para performance, vamos usar um loop python com vértices strided
                stride = 10 # Pula vértices para acelerar load
                for i in range(0, len(pts), stride):
                    ix, iz = idxs_x[i], idxs_z[i]
                    if pts[i, 1] > heightmap[iz, ix]:
                        heightmap[iz, ix] = pts[i, 1]
                        
                self.models[name]['heightmap'] = {
                    'grid': heightmap,
                    'min_x': min_x, 'max_x': max_x,
                    'min_z': min_z, 'max_z': max_z,
                    'step_x': step_x, 'step_z': step_z,
                    'grid_size': grid_size
                }
                print(f"[Renderer3D] Heightmap gerado para '{name}' (Grid {grid_size}x{grid_size})")
            except Exception as e:
                print(f"[Renderer3D] Erro ao gerar heightmap: {e}")

            print(f"[Renderer3D] Modelo '{name}' carregado: {len(indices)} índices")
            return True
            
        except Exception as e:
            print(f"[Renderer3D] Erro ao carregar '{filepath}': {e}")
            return False
    
    def create_sphere(self, name, radius=1.0, segments=32, rings=16, color=(0.7, 0.6, 0.5)):
        """Cria uma esfera procedural (fallback se não tiver modelo)."""
        if not self.initialized:
            return False
        
        vertices = []
        indices = []
        
        for i in range(rings + 1):
            v = i / rings
            phi = v * np.pi
            
            for j in range(segments + 1):
                u = j / segments
                theta = u * 2 * np.pi
                
                x = radius * np.sin(phi) * np.cos(theta)
                y = radius * np.cos(phi)
                z = radius * np.sin(phi) * np.sin(theta)
                
                nx, ny, nz = x / radius, y / radius, z / radius
                
                vertices.extend([x, y, z, nx, ny, nz, u, v])
        
        for i in range(rings):
            for j in range(segments):
                first = i * (segments + 1) + j
                second = first + segments + 1
                
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])
        
        vertices = np.array(vertices, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32)
        
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
            index_buffer=ibo
        )
        
        self.models[name] = {
            'vao': vao,
            'vbo': vbo,
            'ibo': ibo,
            'vertex_count': len(indices),
            'position': glm.vec3(0, 0, 0),
            'rotation': glm.vec3(0, 0, 0),
            'scale': glm.vec3(1, 1, 1),
            'texture': None,
            'tex_scale': 0.02,
            'visible': True
        }
        
        return True
    
    def create_axes(self, name='axes', length=100.0):
        """Cria eixos XYZ para orientação."""
        if not self.initialized:
            return False
            
        # X=Red, Y=Green, Z=Blue
        vertices = np.array([
            0, 0, 0,  1, 0, 0,  0, 0,  # Origin
            length, 0, 0,  1, 0, 0,  0, 0,  # X
            0, 0, 0,  0, 1, 0,  0, 0,  # Origin
            0, length, 0,  0, 1, 0,  0, 0,  # Y
            0, 0, 0,  0, 0, 1,  0, 0,  # Origin
            0, 0, length,  0, 0, 1,  0, 0,  # Z
        ], dtype=np.float32)
        
        # Em modo GL_LINES, não usamos índices complexos
        indices = np.arange(6, dtype=np.uint32)
        
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
            index_buffer=ibo
        )
        
        self.models[name] = {
            'vao': vao,
            'vbo': vbo,
            'ibo': ibo,
            'vertex_count': 6,
            'position': glm.vec3(0, 0, 0),
            'rotation': glm.vec3(0, 0, 0),
            'scale': glm.vec3(1, 1, 1),
            'texture': None,
            'tex_scale': 0.0,
            'visible': True,
            'primitive': moderngl.LINES
        }
        return True

    def set_fog(self, density, color=None):
        """Ajusta parâmetros do fog."""
        self.fog_density = density
        if color:
            self.fog_color = glm.vec3(*color)
        
        if self.initialized:
            self.program['fog_density'].value = density
            self.program['fog_color'].value = tuple(self.fog_color)
    
    def set_camera(self, pos, target=None, up=None):
        """Define posição e orientação da câmera."""
        self.cam_pos = glm.vec3(*pos)
        if target:
            self.cam_target = glm.vec3(*target)
        if up:
            self.cam_up = glm.vec3(*up)
    
    def set_model_transform(self, name, position=None, rotation=None, scale=None):
        """Define transformação de um modelo."""
        if name not in self.models:
            return
        
        model = self.models[name]
        if position:
            model['position'] = glm.vec3(*position)
        if rotation:
            model['rotation'] = glm.vec3(*rotation)
        if scale:
            if isinstance(scale, (int, float)):
                model['scale'] = glm.vec3(scale, scale, scale)
            else:
                model['scale'] = glm.vec3(*scale)
    
    def set_wireframe(self, enabled: bool):
        """Ativa/desativa modo wireframe."""
        if not self.initialized:
            return
        if enabled:
            self.ctx.wireframe = True
        else:
            self.ctx.wireframe = False

    def render(self, clear_color=(0.1, 0.1, 0.1, 1.0)):
        """Renderiza cena para textura e retorna Surface Pygame."""
        if not self.initialized:
            return None
        
        self.fbo.use()
        self.ctx.clear(*clear_color)
        
        # Matrizes de câmera
        view = glm.lookAt(self.cam_pos, self.cam_target, self.cam_up)
        # Aumentado z_far de 1000.0 para 10000.0 para suportar cenários grandes
        projection = glm.perspective(glm.radians(60.0), self.width / self.height, 0.1, 10000.0)
        
        self.program['view'].write(view)
        self.program['projection'].write(projection)
        
        # Renderiza cada modelo
        for name, model in self.models.items():
            if not model.get('visible', True):
                continue
            # Matriz de modelo
            mat = glm.mat4(1.0)
            mat = glm.translate(mat, model['position'])
            mat = glm.rotate(mat, model['rotation'].x, glm.vec3(1, 0, 0))
            mat = glm.rotate(mat, model['rotation'].y, glm.vec3(0, 1, 0))
            mat = glm.rotate(mat, model['rotation'].z, glm.vec3(0, 0, 1))
            mat = glm.scale(mat, model['scale'])
            
            self.program['model'].write(mat)
            if model.get('texture'):
                self.program['use_texture'].value = bool(self._textures_enabled)
                if self._textures_enabled:
                    model['texture'].use(location=0)
                    self.program['tex'].value = 0
                    self.program['tex_scale'].value = float(model.get('tex_scale', 0.02))
                    # Usa modo definido no modelo ou 1 (Triplanar) como fallback
                    self.program['tex_mode'].value = int(model.get('tex_mode', 1))
            else:
                self.program['use_texture'].value = False
                self.program['tex_mode'].value = 0
            
            mode = model.get('primitive', moderngl.TRIANGLES)
            model['vao'].render(mode=mode)
        
        # Lê pixels e converte para Surface Pygame
        data = self.fbo.read(components=4)
        surface = pygame.image.frombuffer(data, (self.width, self.height), 'RGBA')
        surface = pygame.transform.flip(surface, False, True)
        
        return surface
    
    def cleanup(self):
        """Libera recursos."""
        if self.ctx:
            for model in self.models.values():
                model['vao'].release()
                model['vbo'].release()
                model['ibo'].release()
            if self.fbo:
                self.fbo.release()
            if self.texture:
                self.texture.release()
            self.ctx.release()

    def load_texture(self, name, filepath):
        if not self.initialized:
            return False
        try:
            # Tenta usar PIL primeiro para suporte robusto a formatos (TIFF, etc)
            try:
                from PIL import Image
                img = Image.open(filepath)
                img = img.convert('RGBA')
                # Flip vertical para OpenGL (origem embaixo-esquerda)
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                w, h = img.size
                px = img.tobytes()
                print(f"[Renderer3D] Textura carregada via PIL: {filepath} ({w}x{h})")
            except ImportError:
                # Fallback para Pygame se PIL não estiver instalado
                print("[Renderer3D] PIL não encontrado, usando Pygame para carregar textura")
                surf = pygame.image.load(filepath).convert_alpha()
                w, h = surf.get_size()
                px = pygame.image.tobytes(surf, 'RGBA', True)
            except Exception as e:
                print(f"[Renderer3D] Erro no PIL, tentando Pygame: {e}")
                surf = pygame.image.load(filepath).convert_alpha()
                w, h = surf.get_size()
                px = pygame.image.tobytes(surf, 'RGBA', True)

            tex = self.ctx.texture((w, h), 4, data=px)
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            try:
                tex.repeat_x = True
                tex.repeat_y = True
            except Exception:
                pass
            try:
                tex.build_mipmaps()
            except Exception:
                pass
            self.textures[name] = tex
            return True
        except Exception as e:
            print(f"[Renderer3D] Falha ao carregar textura '{filepath}': {e}")
            return False

    def set_model_texture(self, model_name, texture_name):
        if model_name in self.models and texture_name in self.textures:
            self.models[model_name]['texture'] = self.textures[texture_name]
            # Print para debug
            w, h = self.textures[texture_name].size
            print(f"[Renderer3D] Textura '{texture_name}' ({w}x{h}) atribuída ao modelo '{model_name}'")

    def set_model_tex_scale(self, model_name, scale):
        if model_name in self.models:
            self.models[model_name]['tex_scale'] = float(scale)

    def set_model_tex_mode(self, model_name, mode):
        """Define modo de textura (0=UV, 1=Triplanar, 2=Planar)."""
        if model_name in self.models:
            self.models[model_name]['tex_mode'] = int(mode)

    def set_model_visible(self, model_name, visible: bool):
        if model_name in self.models:
            self.models[model_name]['visible'] = bool(visible)

    def set_culling(self, enabled: bool):
        try:
            if enabled:
                self.ctx.enable(moderngl.CULL_FACE)
            else:
                self.ctx.disable(moderngl.CULL_FACE)
        except Exception:
            pass

    def fit_camera_to_model(self, name, margin=1.2):
        if name not in self.models:
            return
        m = self.models[name]
        center = (m['bounds_min'] + m['bounds_max']) * 0.5
        size = m['bounds_size']
        max_dim = max(size.x, size.y, size.z)
        sc = m['scale']
        effective = max_dim * max(sc.x, sc.y, sc.z)
        dist = max(0.5, effective / (2.0 * math.tan(math.radians(60.0) * 0.5)) * margin)
        self.set_camera(pos=(center.x, center.y + effective * 0.1, center.z + dist), target=(center.x, center.y, center.z))

    def set_texture_enabled(self, enabled: bool):
        self._textures_enabled = bool(enabled)

    def get_terrain_height(self, x, z):
        """Retorna a altura do terreno (Y) na posição X, Z do mundo. Verifica todos os modelos canyon."""
        max_y = -99999.0
        
        for name, model in self.models.items():
            if 'canyon' not in name or not model.get('visible', True) or 'heightmap' not in model:
                continue
                
            hm = model['heightmap']
            
            # Transforma Mundo -> Local
            # Assumindo rotação 0 para terrain (otimização)
            pos = model['position']
            scale = model['scale']
            
            lx = (x - pos.x) / scale.x
            lz = (z - pos.z) / scale.z
            
            # Verifica bounds locais
            if (lx >= hm['min_x'] and lx <= hm['max_x'] and
                lz >= hm['min_z'] and lz <= hm['max_z']):
                
                # Mapeia para grid
                gx = int((lx - hm['min_x']) / hm['step_x'])
                gz = int((lz - hm['min_z']) / hm['step_z'])
                
                # Clampa (segurança)
                gx = max(0, min(hm['grid_size'] - 1, gx))
                gz = max(0, min(hm['grid_size'] - 1, gz))
                
                # Amostra altura local
                local_y = hm['grid'][gz, gx]
                
                # Transforma Local -> World
                world_y = (local_y * scale.y) + pos.y
                
                if world_y > max_y:
                    max_y = world_y
                    
        return max_y

    def duplicate_model(self, source_name, new_name):
        """Cria uma instância leve de um modelo existente (compartilha geometria)."""
        if source_name not in self.models:
            return False
        
        src = self.models[source_name]
        # Copia dicionário (referências para VAO/VBO mantidas)
        new_model = src.copy()
        
        # Cria novos vetores de transformação para serem independentes
        new_model['position'] = glm.vec3(src['position'])
        new_model['rotation'] = glm.vec3(src['rotation'])
        new_model['scale'] = glm.vec3(src['scale'])
        
        self.models[new_name] = new_model
        print(f"[Renderer3D] Modelo '{new_name}' duplicado de '{source_name}'")
        return True
