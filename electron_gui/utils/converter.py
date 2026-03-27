""" Converts Lucid *.ts into *.py for the Electron GUI
about this script:
- this script converts the Lucid *.ts files into *.py files for the Electron GUI
- translates the typescript into javascript before converting to python


- target_container path: /app/electron-gui/*  for the Electron GUI
- source_container path: /app/electron-gui/utils/converter.py for the Electron GUI
- uses internal container Directory structure for the conversion
example:
electron_gui/utils/* --> /app/electron-gui/utils/*
electron_gui/main/* --> /app/electron-gui/main/*
electron_gui/renderer/* --> /app/electron-gui/renderer/*
electron_gui/shared/* --> /app/electron-gui/shared/*
electron_gui/assets/* --> /app/electron-gui/assets/*
electron_gui/configs/* --> /app/electron-gui/configs/*
electron_gui/scripts/* --> /app/electron-gui/scripts/*
electron_gui/tests/* --> /app/electron-gui/tests/*
electron_gui/package.json --> /app/electron-gui/package.json

"""
#load imports


# convert Typescript to JavaScript

# convert JavaScript to Python


# save the Python files to the target_container path