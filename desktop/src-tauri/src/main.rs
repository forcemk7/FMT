// Windows GUI app: do not allocate a console window on launch (installer / .exe).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    glassscout_fm26_lib::run();
}
