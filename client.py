from PyQt5 import QtWidgets, QtGui, QtCore
import sys, requests, json, threading, time, argparse
from io import BytesIO
from PIL import Image
import websocket

SERVER_URL = "http://127.0.0.1:8000"

class WSListener(QtCore.QObject):
    message = QtCore.pyqtSignal(dict)
    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self._stop = False
        self._thread = None
        self._ws = None

    def start(self):
        self._stop=False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop=True
        try:
            if self._ws: self._ws.close()
        except: pass

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
            self.message.emit(data)
        except: pass

    def _on_error(self, ws, err): print("WS error", err)
    def _on_close(self, ws, code, msg): print("WS closed")
    def _on_open(self, ws):
        def ping_loop():
            while not self._stop:
                try: ws.send("ping")
                except: break
                time.sleep(20)
        threading.Thread(target=ping_loop, daemon=True).start()

    def _run(self):
        websocket.enableTrace(False)
        self._ws = websocket.WebSocketApp(self.ws_url,
                                          on_open=self._on_open,
                                          on_message=self._on_message,
                                          on_error=self._on_error,
                                          on_close=self._on_close)
        while not self._stop:
            try:
                self._ws.run_forever()
            except: time.sleep(2)

class MainWindow(QtWidgets.QWidget):
    def __init__(self,user:str = 'עדן'):
        super().__init__()
        self.username = user
        self.ws_listener = WSListener("ws://127.0.0.1:8000/ws")
        self.ws_listener.message.connect(self.on_ws_message)
        self.init_ui()
        self.ws_listener.start()
        self.refresh()
        self.need_image = True

    def init_ui(self):
        self.setWindowTitle("Dog Rotator")
        self.resize(600,625)
        v = QtWidgets.QVBoxLayout()

        # ComboBox לבחור משתמש
        h1 = QtWidgets.QHBoxLayout()
        self.combo_user = QtWidgets.QComboBox()
        h1.addWidget(self.combo_user)#,alignment=QtCore.Qt.AlignRight)
        h1.addWidget(QtWidgets.QLabel("בחר ילדה:"))#alignment=QtCore.Qt.AlignRight)
        v.addLayout(h1)

        # יום נוכחי
        self.label_date = QtWidgets.QLabel("...")
        f = self.label_date.font(); f.setPointSize(14); f.setBold(True); self.label_date.setFont(f)
        v.addWidget(self.label_date)

        # מי בתור
        self.label_today = QtWidgets.QLabel("...")
        f2 = self.label_today.font(); f2.setPointSize(16); f2.setBold(True); self.label_today.setFont(f2)
        v.addWidget(self.label_today)

        # תמונה
        self.image_label = QtWidgets.QLabel(); self.image_label.setFixedSize(200,200)
        self.image_label.setStyleSheet('border-radius:100px; background-color:#faf7f0;')
        v.addWidget(self.image_label, alignment=QtCore.Qt.AlignCenter) # type: ignore

        h2 = QtWidgets.QHBoxLayout()
        # כפתור סימנתי הורדה
        btn_refresh = QtWidgets.QPushButton("רענן")
        btn_refresh.clicked.connect(self.refresh)
        h2.addWidget(btn_refresh)

        btn_done = QtWidgets.QPushButton("הורדתי")
        btn_done.clicked.connect(self.mark_done)
        h2.addWidget(btn_done)
        v.addLayout(h2)

        # טבלת משמרות
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["יום","תור מי","סטאטוס ביצוע"])
        v.addWidget(self.table)

        self.setLayout(v)

    def on_ws_message(self,data):
        payload = data.get('payload')
        if payload:
            self.apply_payload(payload)

    def apply_payload(self,payload):
        # ComboBox רשימת ילדות
        self.combo_user.clear()
        self.combo_user.addItems(payload.get('children_list',[]))
        index =  self.combo_user.findText(self.username)
        if index != -1:
            self.combo_user.setCurrentIndex(index)

        # תאריך היום
        today = payload.get('date','')
        wd = payload.get('weekday',0)
        weekdays = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
        self.label_date.setText(f"{weekdays[wd]}, {today}")

        # מי בתור היום
        self.label_today.setText("תור להוריד היום: " + payload.get('today_name','-'))

        # טבלת משמרות
        table = payload.get('shifts_table',{})
        self.table.setRowCount(len(table))
        for i,(day,(name,status)) in enumerate(table.items()):
            self.table.setItem(i,0, QtWidgets.QTableWidgetItem(day))
            self.table.setItem(i,1, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(i,2, QtWidgets.QTableWidgetItem("✅" if status else "❌"))

        # תמונה
        img_path = payload.get('dog_image','')
        if img_path and self.need_image:
            try:
                r = requests.get(SERVER_URL+"/image",stream=True)
                r.raise_for_status() # ensure status code 200 ok
                img_bytes = BytesIO(r.content)
                im = Image.open(img_bytes)
                im.load()
                im = im.convert('RGBA')
                im.thumbnail((200,200))
                data_bytes = im.tobytes('raw','RGBA')
                qimg = QtGui.QImage(data_bytes, im.size[0], im.size[1], QtGui.QImage.Format_RGBA8888)
                pix = QtGui.QPixmap.fromImage(qimg)
                rounded = QtGui.QPixmap(200,200)
                rounded.fill(QtCore.Qt.transparent) # type: ignore
                painter = QtGui.QPainter(rounded)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                path = QtGui.QPainterPath()
                path.addEllipse(0,0,200,200)
                painter.setClipPath(path)
                painter.drawPixmap(0,0,pix)
                painter.end()
                self.image_label.setPixmap(rounded)
                self.need_image = False
            except Exception as e:
                print(f"Image Error: {e}")
                self.image_label.setText("אין תמונה")
        else:
            if self.need_image:
                self.image_label.setText("אין תמונה")
            

    def refresh(self):
        try:
            r = requests.get(SERVER_URL+"/today")
            data = r.json()
            self.apply_payload(data)
        except:
            pass

    def mark_done(self):
        name = self.combo_user.currentText()
        if not name: return
        try:
            requests.post(SERVER_URL+"/mark_done", data={'name':name})
        except:
            pass

    def closeEvent(self,event):
        try: self.ws_listener.stop()
        except: pass
        event.accept()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Dog Rotator")

    # Add arguments
    parser.add_argument("--user", type=str, help="user name reporting",default='שקד')

    # Parse arguments
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(args.user)
    w.show()
    sys.exit(app.exec_())