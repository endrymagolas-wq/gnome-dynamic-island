import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';

const SERVICES = [
    ['airplay-screen.service', 'Відео · Ubuntu Screen'],
    ['ytmusic-airplay.service', 'Музика · Ubuntu PC'],
    ['netflix-remote.service', 'Netflix · пульт'],
];

export class CastControls {
    constructor(path) {
        this.path = path;
    }

    enable() {
        this._alive = true;
        this._busy = false;
        this._updating = false;
        this._generation = 0;
        this._cancellable = new Gio.Cancellable();
        this._available = new Set();
        this._states = Object.fromEntries(SERVICES.map(([unit]) => [unit, false]));

        this._indicator = new QuickSettings.SystemIndicator();
        this._toggle = new QuickSettings.QuickMenuToggle({
            title: 'Cast',
            subtitle: 'Перевіряю…',
            iconName: 'video-display-symbolic',
            toggleMode: true,
        });
        this._toggle.menu.setHeader('video-display-symbolic', 'Cast',
            'AirPlay та Netflix-пульт');
        this._indicator.quickSettingsItems.push(this._toggle);

        this._switches = new Map();
        for (const [unit, label] of SERVICES) {
            const item = new PopupMenu.PopupSwitchMenuItem(label, false);
            const id = item.connect('toggled', (_item, state) => {
                if (!this._updating)
                    this._setService(unit, state);
            });
            this._switches.set(unit, {item, id});
            this._toggle.menu.addMenuItem(item);
        }

        this._toggle.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._openNetflixItem = this._toggle.menu.addAction('Відкрити Netflix на ПК',
            () => this._openNetflix());
        this._pairItem = this._toggle.menu.addAction('Підключити телефон · QR-код',
            () => this._showPairing());
        this._toggle.menu.addAction('Перезапустити приймачі',
            () => this._run(['systemctl', '--user', 'restart',
                ...this._units()]));

        this._toggle.connect('notify::checked', () => {
            if (this._updating || this._busy)
                return;
            if (!this._available.size) return;
            const allReady = this._units().every(unit => this._states[unit]);
            this._run(['systemctl', '--user', allReady ? 'stop' : 'start',
                ...this._units()]);
        });
        this._toggle.menu.connect('open-state-changed', (_menu, open) => {
            if (open)
                this._refresh();
        });

        Main.panel.statusArea.quickSettings.addExternalIndicator(this._indicator);
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 10, () => {
            if (!this._busy)
                this._refresh();
            return GLib.SOURCE_CONTINUE;
        });
        this._refresh();
    }

    _units() { return [...this._available]; }

    _setService(unit, active) {
        if (this._busy)
            return;
        this._run(['systemctl', '--user', active ? 'start' : 'stop', unit]);
    }

    _showPairing() {
        if (!this._states['netflix-remote.service']) {
            this._run(['systemctl', '--user', 'start', 'netflix-remote.service'],
                () => this._launchPairing());
        } else {
            this._launchPairing();
        }
    }

    _launchPairing() {
        this._run(['/usr/bin/python3', GLib.build_filenamev([
            GLib.get_home_dir(), '.local/share/netflix-remote/show-pairing.py',
        ])]);
    }

    _openNetflix() {
        const launch = () => this._run(['/usr/bin/python3',
            GLib.build_filenamev([this.path, 'open-netflix.py'])]);
        if (!this._states['netflix-remote.service'])
            this._run(['systemctl', '--user', 'start', 'netflix-remote.service'], launch);
        else
            launch();
    }

    _run(argv, afterSuccess = null) {
        if (!this._alive || this._busy)
            return;
        this._busy = true;
        this._generation++;
        this._render();
        try {
            const process = Gio.Subprocess.new(argv,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            process.communicate_utf8_async(null, this._cancellable, (proc, result) => {
                if (!this._alive)
                    return;
                let error = null;
                try {
                    const [, , stderr] = proc.communicate_utf8_finish(result);
                    if (!proc.get_successful())
                        error = stderr?.trim() || 'Команда не виконалася';
                } catch (e) {
                    error = e.message;
                }
                this._busy = false;
                if (error) {
                    this._error = error;
                    Main.notifyError('Cast', error);
                } else {
                    this._error = null;
                }
                this._refresh();
                if (!error && afterSuccess)
                    afterSuccess();
            });
        } catch (e) {
            this._busy = false;
            this._error = e.message;
            Main.notifyError('Cast', e.message);
            this._refresh();
        }
    }

    _refresh() {
        if (!this._alive || this._busy)
            return;
        const generation = ++this._generation;
        try {
            const process = Gio.Subprocess.new(['systemctl', '--user', 'show', '--property=LoadState,ActiveState',
                ...SERVICES.map(([unit]) => unit)],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            process.communicate_utf8_async(null, this._cancellable, (proc, result) => {
                if (!this._alive || generation !== this._generation)
                    return;
                try {
                    const [, stdout] = proc.communicate_utf8_finish(result);
                    const blocks = stdout.trim().split(/\n\s*\n/);
                    this._available.clear();
                    SERVICES.forEach(([unit], index) => {
                        const lines = blocks[index]?.split('\n') ?? [];
                        if (lines.includes('LoadState=loaded')) this._available.add(unit);
                        this._states[unit] = lines.includes('ActiveState=active');
                    });
                } catch (e) {
                    this._error = e.message;
                }
                this._render();
            });
        } catch (e) {
            this._error = e.message;
            this._render();
        }
    }

    _render() {
        if (!this._alive)
            return;
        this._updating = true;
        this._toggle.visible = this._available.size > 0;
        const total = this._available.size;
        const count = SERVICES.filter(([unit]) => this._states[unit]).length;
        this._toggle.checked = total > 0 && count === total;
        this._toggle.subtitle = this._error ? 'Помилка · відкрий меню' :
            this._busy ? 'Застосовую…' :
                total > 0 && count === total ? 'Готово' :
                    count === 0 ? 'Вимкнено' : `${count} з ${total} активні`;
        for (const [unit, {item, id}] of this._switches) {
            item.block_signal_handler(id);
            item.setToggleState(this._states[unit]);
            item.unblock_signal_handler(id);
            item.visible = this._available.has(unit);
            item.sensitive = !this._busy;
        }
        this._openNetflixItem.visible = this._available.has('netflix-remote.service');
        this._pairItem.visible = this._available.has('netflix-remote.service');
        this._openNetflixItem.sensitive = !this._busy;
        this._pairItem.sensitive = !this._busy;
        this._updating = false;
    }

    disable() {
        this._alive = false;
        this._cancellable?.cancel();
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = 0;
        this._toggle?.menu.destroy();
        this._indicator?.quickSettingsItems.forEach(item => item.destroy());
        this._indicator?.destroy();
        this._indicator = null;
        this._toggle = null;
        this._switches = null;
        this._cancellable = null;
    }
}
