# xorautomation

## Icon images

Icon images such as button is not included here due to copyright reason.  Please capture it from game.

## PC vs emulator

Automation work on BS emulator by default.  By setting the windows size of PC client same as emulator, and relaxing detection threshold, the same code can be used for Android and PC.  However, some required re-capture of button images.

Specific PC version support is added for commonly used features like: fishing, farming, arm weastling, by adding "-p" option to the script.  Refer to code for details.

## Windows Size

Appraently, operation is window-size dependent.  Use the corresponding script for setting the window size of PC client or BS emulator window.  Full screen resolution is 1920x1080.  Taskbar height is 40px which is default for Windows 10.  Windows 11 PC user please use Winhawk to set taskbar height to 40px.

| Feature  | Size Setting Script |
| ------------ |:-------------:|
| farm -n      | setwin_bluestacks    |
| farm -p -n   | setwin_roxpc         | 
| farm -n      | setwin_bluestacks    |
| farm         | BS window maximized  |
| fish -p      | PC window maximized  |
| buy/sell -p  | setwin_roxpc         |
| buy/sell     | setwin_bluestacks_small |
| runquests -p | setwin_roxpc_full    |
| runquests    | BS window maximized  |
| armw         | setwin_bluestacks / setwin_roxpc | 
| others       | BS window maximized / setwin_roxpc_full |
