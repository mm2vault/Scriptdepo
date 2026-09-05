from flask import Flask, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'gizli-anahtar'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///script.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------- VERİTABANI ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(200))
    email = db.Column(db.String(120))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Script(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    language = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='scripts')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    script_id = db.Column(db.Integer, db.ForeignKey('script.id'))
    author = db.relationship('User', backref='comments')
    script = db.relationship('Script', backref='comments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- HTML ŞABLONLARI ----------
BASE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>ScriptPaylaş</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial; background: #0d1117; color: #c9d1d9; padding: 15px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #30363d; margin-bottom: 20px; }
        .header h1 { color: #58a6ff; font-size: 24px; }
        .nav { display: flex; flex-wrap: wrap; gap: 10px; }
        .nav a, .nav button { color: #8b949e; text-decoration: none; background: none; border: none; cursor: pointer; font-size: 14px; padding: 5px 10px; }
        .nav a:hover, .nav button:hover { color: #58a6ff; }
        .btn { padding: 8px 20px; border-radius: 6px; border: none; cursor: pointer; text-decoration: none; display: inline-block; font-size: 14px; }
        .btn-primary { background: #238636; color: white; }
        .btn-danger { background: #da3633; color: white; }
        .btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
        .card { background: #161b22; padding: 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #30363d; }
        .card h3 { color: #58a6ff; margin-bottom: 10px; }
        .code-block { background: #0d1117; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: monospace; margin: 10px 0; border: 1px solid #30363d; white-space: pre-wrap; font-size: 13px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #8b949e; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; font-size: 14px; }
        .form-group textarea { min-height: 150px; font-family: monospace; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .alert { padding: 12px; border-radius: 6px; margin-bottom: 15px; }
        .alert-success { background: #0f2d1a; border: 1px solid #238636; color: #3fb950; }
        .alert-error { background: #2d0f0f; border: 1px solid #da3633; color: #f85149; }
        .alert-info { background: #0f1d2d; border: 1px solid #1f6feb; color: #58a6ff; }
        .comment { background: #0d1117; padding: 12px; border-radius: 6px; margin: 10px 0; border: 1px solid #30363d; }
        .comment strong { color: #58a6ff; }
        .mt-10 { margin-top: 10px; }
        .flex { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        @media (max-width: 600px) { .header h1 { font-size: 20px; } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📜 ScriptPaylaş</h1>
        <div class="nav">
            <a href="/">Ana Sayfa</a>
            {NAV_LINKS}
        </div>
    </div>
    {FLASH}
    {CONTENT}
</div>
</body>
</html>
'''

def render_page(content, nav_links='', flash=''):
    flash_html = ''
    if flash:
        flash_html = f'<div class="alert alert-{flash[1]}">{flash[0]}</div>'
    return BASE_HTML.replace('{NAV_LINKS}', nav_links).replace('{FLASH}', flash_html).replace('{CONTENT}', content)

# ---------- ROTALAR ----------
@app.route('/')
def index():
    scripts = Script.query.order_by(Script.created_at.desc()).all()
    nav = ''
    if current_user.is_authenticated:
        nav = f'<a href="/upload">📤 Yükle</a><a href="/profile">👤 {current_user.username}</a><a href="/logout">🚪 Çıkış</a>'
    else:
        nav = '<a href="/login">🔑 Giriş</a><a href="/register">📝 Kayıt</a>'
    
    cards = ''
    for s in scripts:
        cards += f'''
        <div class="card">
            <h3>{s.title}</h3>
            <div class="code-block">{s.content[:150]}{'...' if len(s.content)>150 else ''}</div>
            <div class="flex">
                <span style="color:#8b949e;font-size:13px;">💻 {s.language or 'Bilinmiyor'}</span>
                <span style="color:#8b949e;font-size:13px;">👤 {s.author.username}</span>
                <span style="color:#8b949e;font-size:13px;">📅 {s.created_at.strftime('%d.%m.%Y')}</span>
            </div>
            <div class="flex mt-10">
                <a href="/script/{s.id}" class="btn btn-primary">🔍 İncele</a>
                {f'<a href="/delete/{s.id}" class="btn btn-danger" onclick="return confirm(\'Silmek istediğine emin misin?\')">🗑️ Sil</a>' if current_user.is_authenticated and current_user.id == s.user_id else ''}
            </div>
        </div>
        '''
    
    if not scripts:
        cards = '<div class="card"><p>Henüz script yok. İlk scripti sen paylaş! 🚀</p></div>'
    
    return render_page(f'<div class="grid">{cards}</div>', nav)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        language = request.form.get('language')
        if not title or not content:
            flash('Başlık ve kod zorunlu!', 'error')
            return redirect('/upload')
        s = Script(title=title, content=content, language=language, user_id=current_user.id)
        db.session.add(s)
        db.session.commit()
        flash('Script yüklendi! 🎉', 'success')
        return redirect('/')
    
    nav = f'<a href="/">🏠 Ana Sayfa</a><a href="/profile">👤 Profil</a><a href="/logout">🚪 Çıkış</a>'
    content = '''
    <div class="card">
        <h2>📤 Script Yükle</h2>
        <form method="POST">
            <div class="form-group">
                <label>Başlık *</label>
                <input type="text" name="title" required placeholder="Script başlığı...">
            </div>
            <div class="form-group">
                <label>Kod *</label>
                <textarea name="content" required placeholder="Script kodunu yapıştır..."></textarea>
            </div>
            <div class="form-group">
                <label>Dil</label>
                <select name="language">
                    <option value="">Seç</option>
                    <option>Python</option><option>JavaScript</option><option>PHP</option>
                    <option>HTML/CSS</option><option>Shell</option><option>Ruby</option>
                    <option>Go</option><option>Java</option><option>C++</option><option>C</option>
                    <option>Rust</option><option>Diğer</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">📤 Yayınla</button>
            <a href="/" class="btn btn-secondary">İptal</a>
        </form>
    </div>
    '''
    return render_page(content, nav)

@app.route('/script/<int:id>')
def detail(id):
    script = Script.query.get_or_404(id)
    comments = Comment.query.filter_by(script_id=id).order_by(Comment.created_at.desc()).all()
    
    nav = ''
    if current_user.is_authenticated:
        nav = f'<a href="/">🏠 Ana Sayfa</a><a href="/profile">👤 Profil</a><a href="/logout">🚪 Çıkış</a>'
    else:
        nav = '<a href="/">🏠 Ana Sayfa</a><a href="/login">🔑 Giriş</a>'
    
    comment_html = ''
    for c in comments:
        comment_html += f'''
        <div class="comment">
            <strong>{c.author.username}</strong> <span style="color:#8b949e;font-size:12px;">{c.created_at.strftime('%d.%m.%Y %H:%M')}</span>
            <p style="margin-top:5px;">{c.content}</p>
        </div>
        '''
    if not comments:
        comment_html = '<p style="color:#8b949e;">Henüz yorum yok.</p>'
    
    content = f'''
    <div class="card">
        <h2>{script.title}</h2>
        <div class="flex" style="margin:10px 0;">
            <span style="color:#8b949e;">👤 {script.author.username}</span>
            <span style="color:#8b949e;">💻 {script.language or 'Bilinmiyor'}</span>
            <span style="color:#8b949e;">📅 {script.created_at.strftime('%d.%m.%Y %H:%M')}</span>
        </div>
        <div class="code-block">{script.content}</div>
        <div class="flex mt-10">
            <a href="/" class="btn btn-secondary">⬅ Geri</a>
            {f'<a href="/delete/{script.id}" class="btn btn-danger" onclick="return confirm(\'Silmek istediğine emin misin?\')">🗑️ Sil</a>' if current_user.is_authenticated and current_user.id == script.user_id else ''}
        </div>
    </div>
    <div class="card">
        <h3>💬 Yorumlar</h3>
        {f'''
        <form method="POST" action="/comment/{script.id}">
            <div class="form-group">
                <textarea name="content" placeholder="Yorum yaz..." required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">📨 Gönder</button>
        </form>
        ''' if current_user.is_authenticated else '<p>Yorum yapmak için <a href="/login">giriş yapın</a></p>'}
        <hr style="border-color:#30363d;margin:15px 0;">
        {comment_html}
    </div>
    '''
    return render_page(content, nav)

@app.route('/comment/<int:id>', methods=['POST'])
@login_required
def comment(id):
    content = request.form.get('content')
    if content:
        c = Comment(content=content, user_id=current_user.id, script_id=id)
        db.session.add(c)
        db.session.commit()
        flash('Yorum eklendi!', 'success')
    return redirect(f'/script/{id}')

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    s = Script.query.get_or_404(id)
    if s.user_id != current_user.id:
        flash('Yetkin yok!', 'error')
        return redirect('/')
    db.session.delete(s)
    db.session.commit()
    flash('Script silindi.', 'success')
    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter_by(username=u).first()
        if user and user.check_password(p):
            login_user(user)
            flash('Hoş geldin!', 'success')
            return redirect('/')
        flash('Hatalı giriş!', 'error')
    
    content = '''
    <div class="card" style="max-width:400px;margin:auto;">
        <h2 style="text-align:center;">🔑 Giriş</h2>
        <form method="POST">
            <div class="form-group">
                <label>Kullanıcı Adı</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Şifre</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%;">Giriş Yap</button>
        </form>
        <div style="text-align:center;margin-top:15px;">
            <a href="/register" style="color:#58a6ff;">Hesabın yok mu? Kayıt ol</a>
        </div>
    </div>
    '''
    return render_page(content, '<a href="/">🏠 Ana Sayfa</a><a href="/register">📝 Kayıt</a>')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        e = request.form.get('email', '')
        if User.query.filter_by(username=u).first():
            flash('Bu kullanıcı adı alınmış!', 'error')
            return redirect('/register')
        user = User(username=u, email=e)
        user.set_password(p)
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yap.', 'success')
        return redirect('/login')
    
    content = '''
    <div class="card" style="max-width:400px;margin:auto;">
        <h2 style="text-align:center;">📝 Kayıt</h2>
        <form method="POST">
            <div class="form-group">
                <label>Kullanıcı Adı *</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email">
            </div>
            <div class="form-group">
                <label>Şifre *</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%;">Kayıt Ol</button>
        </form>
        <div style="text-align:center;margin-top:15px;">
            <a href="/login" style="color:#58a6ff;">Zaten hesabın var mı? Giriş yap</a>
        </div>
    </div>
    '''
    return render_page(content, '<a href="/">🏠 Ana Sayfa</a><a href="/login">🔑 Giriş</a>')

@app.route('/profile')
@login_required
def profile():
    scripts = Script.query.filter_by(user_id=current_user.id).all()
    nav = f'<a href="/">🏠 Ana Sayfa</a><a href="/upload">📤 Yükle</a><a href="/logout">🚪 Çıkış</a>'
    
    cards = ''
    for s in scripts:
        cards += f'''
        <div class="card">
            <h4>{s.title}</h4>
            <span style="color:#8b949e;font-size:13px;">{s.created_at.strftime('%d.%m.%Y')}</span>
            <div class="flex mt-10">
                <a href="/script/{s.id}" class="btn btn-primary">🔍 Görüntüle</a>
                <a href="/delete/{s.id}" class="btn btn-danger" onclick="return confirm('Silmek istediğine emin misin?')">🗑️ Sil</a>
            </div>
        </div>
        '''
    if not scripts:
        cards = '<div class="card"><p>Henüz scriptin yok. <a href="/upload">İlk scriptini paylaş!</a></p></div>'
    
    content = f'''
    <h2 style="margin-bottom:15px;">👤 {current_user.username}</h2>
    <p style="color:#8b949e;margin-bottom:20px;">📧 {current_user.email or 'Email girilmemiş'}</p>
    <h3 style="margin-bottom:15px;">📜 Scriptlerim ({len(scripts)})</h3>
    <div class="grid">{cards}</div>
    '''
    return render_page(content, nav)

# ---------- FLASH MESAJ DESTEĞİ ----------
def flash(message, category='info'):
    from flask import session
    session['_flash'] = (message, category)

def get_flash():
    from flask import session
    flash_data = session.pop('_flash', None)
    return flash_data

# ---------- BASE RENDER'ı DÜZELT ----------
original_render = render_page
def render_page(content, nav_links='', flash=None):
    if flash is None:
        flash = get_flash()
    flash_html = ''
    if flash:
        flash_html = f'<div class="alert alert-{flash[1]}">{flash[0]}</div>'
    return BASE_HTML.replace('{NAV_LINKS}', nav_links).replace('{FLASH}', flash_html).replace('{CONTENT}', content)

# ---------- FLASK FLASH'ı YENİDEN TANIMLA ----------
def flash(message, category='info'):
    from flask import session
    session['_flash'] = (message, category)

from flask import session as flask_session

# ---------- ÇALIŞTIR ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@admin.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin: admin / admin123")
    
    print("🚀 http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
