# Windows: завантаження й запуск

Реліз **windows-v0.4.0-beta.1** — портативна x64 beta. Перевірено на Windows 11 Pro, build 26200. Острівець, AirPlay та шпалери можна взяти окремо або повним набором.

## Обери архів

| Потрібно | Завантаження | Запуск після розпакування |
| --- | --- | --- |
| Усе разом | [Повний Windows-набір](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/island-desktop-windows-full-0.4.0-beta.1.zip) | `IslandDesktop-Windows-Full/Start-Desktop.cmd` |
| Верхній острівець, dock і медіа | [Острівець Windows](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/island-desktop-windows-0.4.0-beta.1.zip) | `IslandDesktop-Windows/IslandDesktop.exe` |
| Музика й відео з телефона | [AirPlay-приймач](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/cortiva-airplay-windows-0.4.0-beta.1.zip) | `Cortiva-AirPlay-Windows/Start-AirPlay.cmd` |
| Острів із трьома персонажами | [Шпалери V7](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/fairy-lagoon-v7-wallpaper-windows.zip) | `FairyLagoon-V7-Windows/Start-Wallpaper.cmd` |
| Змінити сцену та рухи | [Blender-джерела V7](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/fairy-lagoon-v7-blender-sources.zip) | Відкрити `.blend` у Blender. |

[Код проєкту](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/island-desktop-windows-source-0.4.0-beta.1.zip) · [SHA256SUMS](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/SHA256SUMS) · [Відео](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/island-desktop-windows-demo.mp4)

[Відповідні джерела нативних бібліотек AirPlay](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/cortiva-airplay-native-corresponding-sources-0.4.0-beta.1.zip) доступні окремим asset; їх не потрібно завантажувати для звичайного запуску. Джерела UxPlay і локальний патч уже є в приймачі.

## Повний набір

1. Встанови Lively Wallpaper з офіційної сторінки Microsoft Store.
2. Розпакуй повний архів у постійну папку.
3. Відкрий `Start-Desktop.cmd`.
4. Для телефона ввімкни приймач у **Система → AirPlay**.

.NET, Python і Lively CLI вже включені. Blender потрібен лише для редагування сцени. Lively встановлюється окремо; launcher не завантажує CLI під час першого запуску. Зберігай усі підпапки пакета разом.

## Як користуватися

Наведи курсор на верхній край, трохи відступивши від кутів: відкриється верхня панель. Клік на капсулу відкриває медіа, колесо над нею змінює гучність. Стрілка зверху показує справжні фонові значки Windows.

Нижній dock запускає й перемикає програми; правий клік показує їхні вікна. Значки беруться з програм, установлених на твоєму ПК. Сторонні програми та їхні облікові записи не входять до архіву.

V7 має три окремі місця для персонажів, спільний лежак і чайний столик. Вони гуляють, сідають, п’ють, лежать, чухають пузце й заварюють чай. Освітлення змінюється за часом ПК; у властивостях Lively можна вибрати фазу вручну, якість і воду.

## AirPlay

Телефон і ПК мають бути в одній локальній мережі:

- Музика: обери **Cortiva Island** у меню AirPlay плеєра.
- YouTube: **кнопка трансляції → AirPlay / пристрої Bluetooth → Cortiva Island**. Підтримуване відео відкриється в окремому вікні ПК.
- PIN у повному наборі показує острівець; окремий приймач показує його в консолі.

Для додавання приймача до архіву лише острівця скопіюй всю папку `receiver/` з AirPlay-архіву в `IslandDesktop-Windows/receiver/`, потім увімкни приймач у панелі. Не запускай окрему консоль AirPlay, коли працює приймач острівця.

Якщо firewall блокує з’єднання, у повному чи AirPlay-пакеті запусти кореневий `Enable-AirPlay-Firewall.ps1` від адміністратора. Він додає лише правила конкретного приймача для локальної підмережі; для видалення — `Enable-AirPlay-Firewall.ps1 -Remove`. Для приймача, доданого до core-острівця, використовуй його `airplay-firewall.ps1`. [Докладніше](AIRPLAY_WINDOWS.md).

З реального iPhone підтверджені звук, звук після PIN і рух відео YouTube зі звуком. Це не перевірка кожного iOS-плеєра чи DRM-сервісу. Перемотування та метадані залежать від джерела; 2 / 5 / 8 секунд — ціль буфера, а не гарантована затримка.

## Зупинка й повернення

Повний набір: `Stop-Desktop.cmd` закриває власні процеси, повертає попередній стан taskbar і захоплену конфігурацію Lively. Окремі шпалери: `Restore-Wallpaper.cmd`. Lively глобально не закривається. Якщо попереднього layout немає, повертаються звичайні шпалери Windows.

Лише острівець можна закрити через меню або `stop.ps1`; окремий AirPlay — закривши консоль. Перед видаленням папки вимкни автозапуск, якщо його вмикав. Ключі спарення та налаштування залишаються в локальних даних користувача.

## Межі beta

Windows 10, ARM64, усі DPI/монітори, фізичні lock/sleep/resume та exclusive fullscreen ще потребують ширшої перевірки. Пакет не встановлює Linux Laya/GTK-теми та не вимикає глобально всі popup Windows. Детальні події Claude Code потребують опціональних hooks; інша активність персонажів визначається приблизно з локальних процесів і фокуса.

[Англомовна інструкція](INSTALL_WINDOWS.md) · [V7 і джерела](WALLPAPER_V7.md) · [Перевірки та обмеження](RELEASE_VALIDATION.md)
