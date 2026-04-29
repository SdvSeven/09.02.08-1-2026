import sys, json, os, sqlite3, time
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QTransform
from PyQt6.QtCore import Qt, QSize, QTimer
try:
import serial
HAS_SERIAL = True
except:
HAS_SERIAL = False

# ── Константы ────────────────────────────────────────────────────────────────

M          = r”module1\media”
MAP_FILE   = r”map.json”
DB_FILE    = r”events.db”
LOGO       = f”{M}\TLgreen.png”
IMG1       = f”{M}\Cbottom.png”
IMG2       = f”{M}\Pedestrain.png”
IMG3       = f”{M}\Block.png”
IMG4       = f”{M}\Zhorizontal.png”
IMG5       = f”{M}\TLyellow.png”
RD1        = f”{M}\Rvertical.png”
RD2        = f”{M}\Rcrossroads.png”
TL_RED     = f”{M}\TLred.png”
TL_YELLOW  = f”{M}\TLyellow.png”
TL_GREEN   = f”{M}\TLgreen.png”
TL_CYCLE   = [TL_RED, TL_YELLOW, TL_GREEN]
TL_CMD     = {TL_RED: b”R”, TL_YELLOW: b”Y”, TL_GREEN: b”G”}
PLACE_IMGS = [IMG1, IMG2, IMG3, IMG4, IMG5, RD1, RD2]
ROADS      = {RD1, RD2}
FREE       = {IMG2, IMG3}
ROT        = {IMG1, IMG2, IMG4, IMG5}
CYCLES     = {
IMG1: [IMG1, f”{M}\BCvertical.png”, f”{M}\GCicon.ico”],
IMG3: [IMG3, f”{M}\Stop.png”, f”{M}\Start.png”],
}
CELL, COLS, ROWS = 36, 21, 21

# ── БД ───────────────────────────────────────────────────────────────────────

def init_db():
con = sqlite3.connect(DB_FILE)
con.execute(“CREATE TABLE IF NOT EXISTS events “
“(id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, event TEXT)”)
con.commit()
con.close()

def log(event):
con = sqlite3.connect(DB_FILE)
con.execute(“INSERT INTO events(time, event) VALUES(?, ?)”,
(time.strftime(”%Y-%m-%d %H:%M:%S”), event))
con.commit()
con.close()

# ── Arduino ───────────────────────────────────────────────────────────────────

class Arduino:
def **init**(self, port):
self._ser = None
if HAS_SERIAL and port:
try:
self._ser = serial.Serial(port, 9600, timeout=1)
time.sleep(2)          # ждём перезагрузку Arduino
except Exception as e:
print(f”Arduino: {e}”)

```
def send_tl(self, tl_path):
    cmd = TL_CMD.get(tl_path)
    if cmd and self._ser:
        try:
            self._ser.write(cmd)
            self._ser.flush()
        except Exception as e:
            print(f"Serial write: {e}")
```

ARD = None

# ── Вспомогательные функции ───────────────────────────────────────────────────

def get_px(path, rot=0):
px = QPixmap(path)
if rot and not px.isNull():
px = px.transformed(QTransform().rotate(rot))
return px

def new_obj(path):
return {“path”: path, “base”: path, “rot”: 0, “speed”: 0}

def parse_dict(d):
return {tuple(map(int, k.split(”,”))): v for k, v in d.items()}

# ── Grid (сетка) ──────────────────────────────────────────────────────────────

class Grid(QWidget):
def **init**(self, side):
super().**init**()
self.setFixedSize(COLS * CELL, ROWS * CELL)
self.setMouseTracking(True)
self.side  = side
self.roads = {}
self.objs  = {}
self.mode  = None
self.sel   = None
self._tip  = QLabel(self)
self._tip.setStyleSheet(
“background:#444; color:#fff; padding:2px 5px; border-radius:3px;”)
self._tip.hide()

```
def mouseMoveEvent(self, e):
    x = int(e.position().x() // CELL)
    y = int(e.position().y() // CELL)
    if 0 <= x < COLS and 0 <= y < ROWS:
        self._tip.setText(f"x:{x} y:{y}")
        self._tip.adjustSize()
        self._tip.move(int(e.position().x()) + 10, int(e.position().y()) + 14)
        self._tip.show()
    else:
        self._tip.hide()

def leaveEvent(self, _):
    self._tip.hide()

def paintEvent(self, _):
    p = QPainter(self)
    p.fillRect(self.rect(), QColor(235, 235, 235))
    for layer in (self.roads, self.objs):
        for (x, y), o in layer.items():
            img = get_px(o["path"], o["rot"])
            if not img.isNull():
                p.drawPixmap(x * CELL, y * CELL, CELL, CELL, img)
    p.setPen(QPen(QColor(0, 0, 0, 50)))
    for i in range(COLS + 1):
        p.drawLine(i * CELL, 0, i * CELL, ROWS * CELL)
    for i in range(ROWS + 1):
        p.drawLine(0, i * CELL, COLS * CELL, i * CELL)

def mousePressEvent(self, e):
    if e.button() != Qt.MouseButton.LeftButton:
        return
    x = int(e.position().x() // CELL)
    y = int(e.position().y() // CELL)
    if not (0 <= x < COLS and 0 <= y < ROWS):
        return
    c = (x, y)
    if self.mode == 'place' and self.sel:
        layer = self.roads if self.sel in ROADS else self.objs
        if c in self.roads or self.sel in FREE | ROADS:
            layer[c] = new_obj(self.sel)
    else:
        o = self.objs.get(c) or self.roads.get(c)
        if o:
            self.side.show_props(c, o, self)
    self.update()

def save(self, path):
    def ser(d):
        return {f"{k[0]},{k[1]}": v for k, v in d.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"roads": ser(self.roads), "objs": ser(self.objs)}, f, indent=2)

def load(self, path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.roads = parse_dict(data.get("roads", {}))
        self.objs  = parse_dict(data.get("objs",  {}))
    except Exception:
        pass
```

# ── Side (боковая панель) ─────────────────────────────────────────────────────

class Side(QWidget):
def **init**(self):
super().**init**()
self.setFixedWidth(120)
self.grid       = None
self.ibtns      = []
self._auto_obj  = None
self._auto_grid = None
self._auto_timer = QTimer()
self._auto_timer.setInterval(3000)
self._auto_timer.timeout.connect(self._auto_tick)

```
    vb = QVBoxLayout(self)
    vb.setContentsMargins(6, 6, 6, 6)
    vb.setSpacing(4)

    self.sp    = self._make_icon_section(PLACE_IMGS)
    self.props = QWidget()
    self.pvb   = QVBoxLayout(self.props)
    self.pvb.setContentsMargins(0, 0, 0, 0)
    self.pvb.setSpacing(4)

    for w in (self.sp, self.props):
        w.hide()
        vb.addWidget(w)
    vb.addStretch()

def _make_icon_section(self, paths):
    w  = QWidget()
    vb = QVBoxLayout(w)
    vb.setContentsMargins(0, 0, 0, 0)
    for p in paths:
        b = QPushButton()
        b.setFixedSize(100, 100)
        b.setCheckable(True)
        b.setProperty("path", p)
        ic = get_px(p)
        if not ic.isNull():
            b.setIcon(QIcon(ic))
            b.setIconSize(QSize(88, 88))
        else:
            b.setText(os.path.basename(p)[:8])
        b.clicked.connect(self._on_icon_click)
        vb.addWidget(b)
        self.ibtns.append(b)
    return w

def _on_icon_click(self):
    sender = self.sender()
    for b in self.ibtns:
        if b is not sender:
            b.setChecked(False)
    if self.grid:
        self.grid.sel = sender.property("path") if sender.isChecked() else None

def switch(self, place=False):
    for b in self.ibtns:
        b.setChecked(False)
    if self.grid:
        self.grid.sel  = None
        self.grid.mode = 'place' if place else None
    self.props.hide()
    self.sp.setVisible(place)

def _add_btn(self, label, slot, checkable=False):
    b = QPushButton(label)
    b.setCheckable(checkable)
    b.clicked.connect(slot)
    self.pvb.addWidget(b)
    return b

def show_props(self, cell, obj, grid):
    self._auto_timer.stop()
    while self.pvb.count():
        w = self.pvb.takeAt(0).widget()
        if w:
            w.deleteLater()
    self.props.show()
    base = obj["base"]
    self.pvb.addWidget(QLabel(f"<b>{os.path.basename(base)}</b>"))

    if base in ROT:
        self._add_btn("Повернуть",
            lambda: (obj.update(rot=(obj["rot"] + 90) % 360), grid.update()))

    if base in CYCLES:
        cycle = CYCLES[base]
        def on_change_type(_, o=obj, c=cycle):
            i = c.index(o["path"]) if o["path"] in c else 0
            o["path"] = c[(i + 1) % len(c)]
            grid.update()
        self._add_btn("Изменить тип", on_change_type)

    if base == IMG5:
        def on_manual(_, o=obj, g=grid):
            idx = TL_CYCLE.index(o["path"]) if o["path"] in TL_CYCLE else 0
            o["path"] = TL_CYCLE[(idx + 1) % 3]
            if ARD: ARD.send_tl(o["path"])
            log(f"Ручной: {os.path.basename(o['path'])}")
            g.update()
        self._add_btn("Ручной режим", on_manual)

        def on_auto_toggle(checked, o=obj, g=grid):
            if checked:
                self._auto_obj  = o
                self._auto_grid = g
                self._auto_timer.start()
                log("Авторежим вкл")
            else:
                self._auto_timer.stop()
                log("Авторежим выкл")
        self._add_btn("Автоматический режим", on_auto_toggle, checkable=True)

    if base == IMG2:
        lbl = QLabel(f"Скорость: {obj.get('speed', 0)} сек")
        self.pvb.addWidget(lbl)
        for txt, delta in (("+1", 1), ("-1", -1)):
            def on_speed(_, o=obj, d=delta, l=lbl):
                o["speed"] = o.get("speed", 0) + d
                l.setText(f"Скорость: {o['speed']} сек")
            self._add_btn(txt, on_speed)

    def on_delete(_, c=cell, g=grid):
        g.objs.pop(c, None)
        g.roads.pop(c, None)
        g.update()
        self.props.hide()
        self._auto_timer.stop()
    b = self._add_btn("Удалить", on_delete)
    b.setStyleSheet("color: red;")

def _auto_tick(self):
    if not self._auto_obj:
        return
    o   = self._auto_obj
    idx = TL_CYCLE.index(o["path"]) if o["path"] in TL_CYCLE else 0
    o["path"] = TL_CYCLE[(idx + 1) % 3]
    if self._auto_grid:
        self._auto_grid.update()
    if ARD:
        ARD.send_tl(o["path"])
    log(f"Авто: {os.path.basename(o['path'])}")
```

# ── App (главное окно) ────────────────────────────────────────────────────────

class App(QMainWindow):
def **init**(self):
super().**init**()
self.setWindowTitle(“Интеллектуальная Дорожная Система”)
lp = QPixmap(LOGO)
if not lp.isNull():
self.setWindowIcon(QIcon(lp))

```
    self.side = Side()
    self.grid = Grid(self.side)
    self.side.grid = self.grid

    central = QWidget()
    self.setCentralWidget(central)
    root = QVBoxLayout(central)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    body = QHBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(0)
    body.addWidget(self.side)
    body.addWidget(self.grid)
    root.addLayout(body)

    bar = QHBoxLayout()
    bar.setContentsMargins(6, 6, 6, 6)
    bar.setSpacing(6)

    self.bp = QPushButton("Добавить объекты")
    self.bp.setCheckable(True)
    self.bp.toggled.connect(lambda v: self.side.switch(place=v))

    btn_save = QPushButton("Сохранить")
    btn_save.clicked.connect(self._save)

    btn_load = QPushButton("Загрузить")
    btn_load.clicked.connect(self._load)

    for b in (self.bp, btn_save, btn_load):
        b.setFixedHeight(32)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.addWidget(b)
    root.addLayout(bar)
    self.adjustSize()

def _save(self):
    fn, _ = QFileDialog.getSaveFileName(self, "Сохранить", "", "JSON (*.json)")
    if fn:
        self.grid.save(fn)

def _load(self):
    fn, _ = QFileDialog.getOpenFileName(self, "Загрузить", "", "JSON (*.json)")
    if fn:
        self.grid.load(fn)
        self.grid.update()
```

# ── Запуск ────────────────────────────────────────────────────────────────────

if **name** == “**main**”:
app = QApplication(sys.argv)
init_db()

```
port, ok = QInputDialog.getText(None, "Arduino", "COM-порт (например COM3), или пусто:")
ARD = Arduino(port.strip() if ok and port.strip() else None)

w = App()
w.show()
QTimer.singleShot(0, lambda: (w.grid.load(MAP_FILE), w.grid.update()))
sys.exit(app.exec())
```
