# ===== server_fastapi.py =====
"""
FastAPI server for Dog Walk Rotator
- רשימת הילדות קבועה
- חלוקת ימי חול לפי weekday_schedule
- שבת עם לוגיקה דינמית
- WebSocket לעדכון בזמן אמת
"""
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect,Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, asyncio, datetime
import aiosqlite

DB = 'dogrotadb.sqlite'
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def init_db():
    if not os.path.exists(DB):
        async with aiosqlite.connect(DB) as db:
            await db.execute('''
                CREATE TABLE children (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            ''')
            await db.execute('''
                CREATE TABLE meta (
                    k TEXT PRIMARY KEY,
                    v TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE weekday_schedule (
                    wd INTEGER PRIMARY KEY,
                    name TEXT,
                    status BOOL,
                    reporter TEXT,
                    date TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE history (
                    date TEXT PRIMARY KEY,
                    wd TEXT,
                    name TEXT,
                    reporter TEXT
                )
            ''')
            await db.execute("INSERT INTO children (id,name) VALUES ('0','עדן')")
            await db.execute("INSERT INTO children (id,name) VALUES ('1','שקד')")

            await db.execute("INSERT INTO meta (k,v) VALUES ('saturday_current_index','0')")
            await db.execute("INSERT INTO meta (k,v) VALUES ('saturday_next_index','0')")
            await db.execute("INSERT INTO meta (k,v) VALUES ('dog_name','לאקי')")
            await db.execute("INSERT INTO meta (k,v) VALUES ('dog_image','/Users/nc/code/DogRotator/dog.jpeg')")

            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('0','עדן',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('1','שקד',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('2','עדן',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('3','שקד',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('4','עדן',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('5','שקד',False)")
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES ('6','עדן',False)")
            await db.commit()

async def get_children_list(db):
    cur = await db.execute('SELECT id,name FROM children ORDER BY id')
    rows = await cur.fetchall()
    return [name for _,name in rows]
async def get_meta_dict(db):
    cur = await db.execute('SELECT k,v FROM meta')
    rows = await cur.fetchall()
    return {r[0]: r[1] for r in rows}

async def get_wd_scheduled(db):
    cur = await db.execute('SELECT wd,name,status,reporter,date FROM weekday_schedule')
    rows = await cur.fetchall()
    return {int(r[0]): str(r[1]) for r in rows}, [bool(r[2]) for r in rows],{int(r[0]):(str(r[3]),str(r[4])) for r in rows}

# ---- קבועות ----
# children_list = ['עדן', 'שקד']
# weekday_schedule = {0:'עדן', 1:'שקד', 2:'עדן', 3:'שקד', 4:'עדן',5:'שקד',6:'עדן'}  # 0=יום ראשון
# weekday_status:list[bool] = [False]*7
# saturday_next_index = 0
# saturday_current_index = 0
# dog_name = 'לאקי'
# dog_image_path = '/Users/nc/code/DogWalkingManager/dog.jpeg'  # example: 'uploads/dog.png'


# WebSocket connections
connections = set()
lock = asyncio.Lock()

# ---- פונקציות עזר ----
def get_today():
    return datetime.date.today()

def get_weekday():
    return get_today().weekday()  # 0=Monday

async def get_saturday_name():
    # global saturday_next_index,saturday_current_index
    async with aiosqlite.connect(DB) as db:
        children_list = await get_children_list(db)
        meta = await get_meta_dict(db)
        return children_list[int(meta['saturday_current_index']) % len(children_list)]

async def build_shifts_table():
    # מחזיר dict: יום -> מי בתור
    table = {}
    weekdays = ['ראשון','שני','שלישי','רביעי','חמישי','שישי','שבת']
    async with aiosqlite.connect(DB) as db:
        weekday_schedule,weekday_status,reporter = await get_wd_scheduled(db)
    
    for wd in range(0,7):
        if wd == 6: # Saturday
            table[f'יום {weekdays[wd]}'] = (await get_saturday_name(),weekday_status[wd],reporter.get(wd,('-','-')))
        else:
            table[f'יום {weekdays[wd]}'] = (weekday_schedule.get(wd,'-'),weekday_status[wd],reporter.get(wd,('-','-')))
    # # שבת
    # table['שבת'] = get_saturday_name()
    return table

async def build_payload():
    # global weekday_status, saturday_current_index,saturday_next_index
    async with aiosqlite.connect(DB) as db:
        children_list = await get_children_list(db)
        meta = await get_meta_dict(db)
        weekday_schedule,weekday_status,_ = await get_wd_scheduled(db)
        today = get_today()
        weekday = get_weekday() # 0 = Monday
        weekday_ = (weekday+1)%7 # 0 = Sunday
        is_weekday = weekday_ < 6
        is_new_week = any(weekday_status[weekday_+1:]) if is_weekday else False

        if is_new_week:
            #update DB
            for wd,_ in enumerate(weekday_schedule):
                await db.execute("UPDATE weekday_schedule SET status=?, reporter=?, date=? WHERE wd=?",(False,"","",wd))


            # meta['saturday_current_index'] = meta['saturday_next_index']
            #update DB
            await db.execute("UPDATE meta SET v=? WHERE k=? ",(meta['saturday_next_index'],'saturday_current_index'))
            
            await db.commit()
        today_name = weekday_schedule.get(weekday_,'-') if is_weekday else await get_saturday_name()

        
    payload = {
        'date': today.isoformat(),
        'weekday': weekday_,
        'today_name': today_name,
        'children_list': children_list,
        'shifts_table': await build_shifts_table(),
        'dog_name': meta['dog_name'],
        'dog_image': meta['dog_image']
    }
    return payload

async def broadcast_update():
    payload = await build_payload()
    msg = json.dumps({'type':'update','payload':payload})
    async with lock:
        to_remove = []
        for ws in list(connections):
            try:
                await ws.send_text(msg)
            except:
                to_remove.append(ws)
        for ws in to_remove:
            connections.discard(ws)

# ---- API ----
@app.on_event('startup')
async def startup():
    await init_db()

@app.get('/today')
async def api_today():
    payload = await build_payload()
    return payload

@app.post('/mark_done')
async def api_mark_done(name:str = Form(...)):
    # global saturday_next_index,saturday_current_index
    # global weekday_status
    async with aiosqlite.connect(DB) as db:
        children_list = await get_children_list(db)
        meta = await get_meta_dict(db)
        weekday_schedule,weekday_status,_ = await get_wd_scheduled(db)
        if name not in children_list:
            raise HTTPException(status_code=400, detail='שם לא חוקי')
        wd = get_weekday()
        wd_ = (wd+1)%7 # convert from 0 = Monday to 0 = Sunday
        if wd_ == 6:  # שבת
            # אם הילדה בתור נכון, קדם את saturday_next_index
            if children_list[int(meta['saturday_current_index']) % len(children_list)] == name:
                saturday_next_index = (int(meta['saturday_current_index']) + 1) % len(children_list)
                #update DB
                await db.execute("UPDATE meta SET v=? WHERE k=?",(saturday_next_index,'saturday_next_index'))
            else:
                saturday_next_index = int(meta['saturday_current_index'])
                await db.execute("UPDATE meta SET v=? WHERE k=?",(saturday_next_index,'saturday_next_index'))
                
        # ימי חול לא משנה את הרשימה
        # weekday_status[wd_] = True 
        #update status for today
        await db.execute("UPDATE weekday_schedule SET status=?, reporter=?,date=? WHERE wd=?",(True,name,get_today().isoformat(),wd_))
        await db.commit()
        await broadcast_update()
        return {'status':'ok'}

@app.post('/upload_image')
async def upload_image(file: bytes):
    # global dog_image_path
    
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    fname = 'uploads/dog_image.png'
    with open(fname,'wb') as f:
        f.write(file)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE meta SET dog_image=?",fname)
        await db.commit()
        # meta = await get_meta_dict(db)
    # dog_image = fname
    await broadcast_update()
    return {'status':'ok','file':fname}

@app.get('/image')
async def get_image():
    async with aiosqlite.connect(DB) as db:
        meta = await get_meta_dict(db)
        dog_image_path = meta['dog_image']
    if dog_image_path and os.path.exists(dog_image_path):
        ext = os.path.splitext(dog_image_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            media_type = "image/jpeg"
        elif ext == '.png':
            media_type = "image/png"
        else:
            media_type = "application/octet-stream"
        return FileResponse(dog_image_path, media_type=media_type)
    else:
        raise HTTPException(status_code=404, detail="אין תמונה")

@app.post('/update_children')
async def update_children(children:list[str] = Form(...)):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM children")
        for id,child in enumerate(children):
            await db.execute("INSERT INTO children (id,name) VALUES (?,?)",(id,child))
        await db.commit()
        children_list = await get_children_list(db)
        return {'status':'ok', 'children':children_list}

@app.post('/update_schedule')
async def update_schedule(schedule:dict):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM weekday_schedule")
        for item in schedule.items():
            await db.execute("INSERT INTO weekday_schedule (wd,name,status) VALUES (?,?,?)",(item[0],item[1][0],item[1][1])) # type: ignore
        await db.commit()
        weekday_schedule = await get_wd_scheduled(db)
        return {'status':'ok', 'schedule':weekday_schedule}
# ---- WebSocket ----
@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    async with lock:
        connections.add(ws)
    try:
        # שלח מיד את המצב הנוכחי
        await ws.send_text(json.dumps({'type':'init','payload':await build_payload()}))
        while True:
            try:
                await ws.receive_text()  # keep alive
            except WebSocketDisconnect:
                break
            except:
                await asyncio.sleep(0.1)
    finally:
        async with lock:
            connections.discard(ws)
if __name__ == '__main__':
    uvicorn.run(app=app)