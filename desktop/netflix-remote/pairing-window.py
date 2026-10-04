#!/usr/bin/python3
"""Show the Netflix phone-pairing QR in a dedicated desktop window."""

from pathlib import Path
import sys

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk


def main() -> None:
    qr_path = Path(sys.argv[1]).resolve()
    if not qr_path.is_file():
        raise SystemExit(f'QR-код не знайдено: {qr_path}')

    app = Gtk.Application(application_id='org.avalon.NetflixPairing',
                          flags=Gio.ApplicationFlags.FLAGS_NONE)
    app.register(None)
    if app.get_is_remote():
        app.activate()
        return

    css = Gtk.CssProvider()
    css.load_from_data(b'''
        window { background: #111215; }
        .pairing-title { color: #f9f7f4; font-size: 28px; font-weight: 700; }
        .pairing-eyebrow { color: #ff775e; font-size: 12px; font-weight: 700; }
        .pairing-copy { color: #b8bac2; font-size: 14px; }
        .pairing-qr { background: white; border-radius: 18px; padding: 17px; }
        .pairing-button { background: #e95420; color: white; border-radius: 11px;
                          padding: 9px 24px; font-weight: 700; border: none; }
        .pairing-button:hover { background: #fa6531; }
    ''')
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    window = Gtk.ApplicationWindow(application=app)
    window.set_title('Netflix · підключити телефон')
    window.set_name('netflix-pairing')
    window.set_default_size(430, 590)
    window.set_resizable(False)
    window.set_position(Gtk.WindowPosition.NONE)
    window.connect('destroy', lambda _window: app.quit())

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_border_width(29)
    window.add(content)

    eyebrow = Gtk.Label(label='NETFLIX · КІНОПУЛЬТ')
    eyebrow.get_style_context().add_class('pairing-eyebrow')
    eyebrow.set_xalign(0)
    content.pack_start(eyebrow, False, False, 0)

    title = Gtk.Label(label='Пульт у твоєму телефоні')
    title.get_style_context().add_class('pairing-title')
    title.set_xalign(0)
    title.set_margin_top(11)
    content.pack_start(title, False, False, 0)

    hint = Gtk.Label(label='Відскануй код камерою iPhone. Телефон і ПК мають бути в одній мережі Wi-Fi.')
    hint.get_style_context().add_class('pairing-copy')
    hint.set_line_wrap(True)
    hint.set_max_width_chars(40)
    hint.set_xalign(0)
    hint.set_margin_top(9)
    content.pack_start(hint, False, False, 0)

    qr_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    qr_frame.get_style_context().add_class('pairing-qr')
    qr_frame.set_halign(Gtk.Align.CENTER)
    qr_frame.set_margin_top(26)
    image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(str(qr_path)))
    qr_frame.pack_start(image, False, False, 0)
    content.pack_start(qr_frame, False, False, 0)

    footer = Gtk.Label(label='Після підключення в Safari натисни «Поділитися» → «На початковий екран».')
    footer.get_style_context().add_class('pairing-copy')
    footer.set_line_wrap(True)
    footer.set_max_width_chars(40)
    footer.set_xalign(0)
    footer.set_margin_top(25)
    content.pack_start(footer, False, False, 0)

    close = Gtk.Button(label='Готово')
    close.get_style_context().add_class('pairing-button')
    close.set_halign(Gtk.Align.END)
    close.set_margin_top(23)
    close.connect('clicked', lambda _button: window.close())
    content.pack_start(close, False, False, 0)

    def release_topmost() -> bool:
        window.set_keep_above(False)
        return GLib.SOURCE_REMOVE

    placed = False

    def present(_app: Gtk.Application) -> None:
        nonlocal placed
        image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(str(qr_path)))
        window.show_all()
        if not placed:
            monitor = Gdk.Display.get_default().get_primary_monitor()
            if monitor:
                workarea = monitor.get_workarea()
                width, height = window.get_size()
                window.move(workarea.x + workarea.width - width - 42,
                            workarea.y + max(24, (workarea.height - height) // 2))
            placed = True
        window.set_keep_above(True)
        window.present()
        GLib.timeout_add_seconds(5, release_topmost)

    app.connect('activate', present)
    app.run([sys.argv[0]])


if __name__ == '__main__':
    main()
