# -*- coding: utf-8 -*-
"""
generate_password_override.py - создаёт (или меняет) резервный аварийный
пароль на ЭТОМ компьютере.

Это НЕ часть самой программы PumpTestApp - отдельная утилита, запускается
вручную, когда нужно создать/сменить локальный резервный пароль.

Как использовать:
    1. Положить этот файл рядом с папкой src программы (то есть на том
       же уровне, где лежит сама папка src)
    2. Запустить: python generate_password_override.py
    3. Ввести желаемый резервный пароль дважды (для подтверждения)
    4. Готово - резервный пароль теперь работает на этом компьютере, в
       дополнение к основному паролю (см. src/auth.py) - подходит любой
       из двух

Резервный пароль хранится не в открытом виде, а в виде хеша (см.
подробное объяснение в src/auth.py) - в скрытом файле, чтобы не
попадаться на глаза при обычном просмотре папки программы.

Чтобы убрать резервный пароль совсем (оставить только основной) -
просто удалить папку .pumpapp_sys рядом с программой.
"""
import os
import sys
import hashlib
import getpass
import ctypes


_OVERRIDE_DIR_NAME = ".pumpapp_sys"
_OVERRIDE_FILE_NAME = "sys.dat"


def _hide_on_windows(path):
    """Помечает файл/папку как скрытые средствами Windows - не
    настоящая защита, просто чтобы не мозолили глаза при обычном
    просмотре содержимого папки в проводнике."""
    if sys.platform != 'win32':
        return
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    override_dir = os.path.join(base_dir, _OVERRIDE_DIR_NAME)
    override_path = os.path.join(override_dir, _OVERRIDE_FILE_NAME)

    print("Создание резервного (аварийного) пароля для этого компьютера.")
    print("Он будет работать в ДОПОЛНЕНИЕ к основному паролю программы,")
    print("а не вместо него.\n")

    password = getpass.getpass("Введите новый резервный пароль: ")
    if not password:
        print("Пароль не может быть пустым - отменено.")
        return
    confirm = getpass.getpass("Повторите пароль: ")
    if password != confirm:
        print("Пароли не совпадают - отменено.")
        return

    os.makedirs(override_dir, exist_ok=True)
    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    with open(override_path, 'w', encoding='utf-8') as f:
        f.write(password_hash)

    _hide_on_windows(override_dir)
    _hide_on_windows(override_path)

    print(f"\nГотово. Резервный пароль сохранён и будет работать на этом компьютере.")
    print(f"Файл (скрытый): {override_path}")


if __name__ == '__main__':
    main()