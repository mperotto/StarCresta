@echo off
echo Instalando PyInstaller...
pip install pyinstaller

echo.
echo Criando executavel do jogo...
echo Isso pode levar alguns minutos.

pyinstaller --noconfirm --onedir --windowed --name "StarCresta" ^
    --add-data "assets;assets" ^
    --add-data "sound;sound" ^
    --add-data "src;src" ^
    main.py

echo.
echo ========================================================
echo CONCLUIDO!
echo.
echo O jogo esta na pasta: dist\StarCresta
echo.
echo Para compartilhar:
echo 1. Entre na pasta 'dist'
echo 2. Clique com botao direito na pasta 'StarCresta'
echo 3. Enviar para -> Pasta compactada (zip)
echo 4. Envie o arquivo .zip para seus amigos!
echo ========================================================
pause
