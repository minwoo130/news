import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from urllib.parse import quote, unquote  # URL 인코딩/디코딩을 위한 임포트

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 꼭 변경하세요!

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# 데이터베이스 연결 함수
def get_db_connection():
    return pymysql.connect(
        host='10.10.8.9',
        user='minwoo',
        password='dkagh1.',  # 실제 비밀번호로 변경
        db='newsdb',
        charset='utf8mb4'
    )

# 뉴스 API에서 뉴스 가져오는 함수
def get_news(query="속보"):
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': query,
        'language': 'ko',
        'pageSize': 5,
        'apiKey': NEWSAPI_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    articles = data.get("articles", [])

    # 기사 URL을 디코딩
    for article in articles:
        article['url'] = unquote(article['url'])  # URL을 디코딩하여 저장

    return articles





    return data.get("articles", [])

# URL 인코딩 필터 (Jinja2 템플릿에서 사용할 수 있도록 등록)
@app.template_filter('url_decode')
def url_decode(value):
    return unquote(value)

# 홈페이지 라우트
@app.route('/', methods=['GET'])
def index():
    username = session.get('username')
    query = request.args.get('query', '').strip()
    if not query:
        query = '속보'

    try:
        articles = get_news(query)
        print(f"검색어: {query}, 기사 수: {len(articles)}")
    except Exception as e:
        return f"<h1>오류 발생</h1><p>{str(e)}</p>"

    return render_template("index.html", articles=articles, query=query, username=username)

# 회원가입 라우트
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            flash('아이디와 비밀번호를 모두 입력하세요.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
            flash('회원가입 완료! 로그인 해주세요.')
            return redirect(url_for('login'))
        except pymysql.err.IntegrityError:
            flash('이미 존재하는 사용자명입니다.')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

# 로그인 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user is None or user[0] is None:
            flash("Invalid username or password")
            return redirect('/login')

        password_hash = user[0]

        if check_password_hash(password_hash, password):
            session['username'] = username
            flash('로그인 성공!')
            return redirect(url_for('index'))
        else:
            flash('아이디 또는 비밀번호가 틀렸습니다.')
            return redirect('/login')

    return render_template('login.html')

# 로그아웃 라우트
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('index'))

# 스크랩 뉴스 추가 라우트
@app.route('/favorite', methods=['POST'])
def add_favorite():
    username = session.get('username')

    if not username:
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    title = request.form.get('title')
    url = request.form.get('url')
    summary = request.form.get('summary', '')

    if not url:
        flash("올바른 URL을 입력해주세요.")
        return redirect('/')

    # URL 인코딩 처리
    encoded_url = quote(url, safe=':/?&=')

    conn = get_db_connection()
    cursor = conn.cursor()

    # 사용자 ID 조회
    cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user = cursor.fetchone()

    if user:
        user_id = user[0]
        cursor.execute(
            "INSERT INTO favorites (user_id, username, title, url, summary) VALUES (%s, %s, %s, %s, %s)",
            (user_id, session['username'], title, encoded_url, summary)
        )
        conn.commit()
        flash('스크랩 완료!')
    else:
        flash('사용자 정보를 찾을 수 없습니다.')

    cursor.close()
    conn.close()
    return redirect('/')

# 내 스크랩 뉴스 목록 라우트
@app.route('/favorites')
def favorites():
    if 'username' not in session:
        flash('로그인 후 이용해주세요.')
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM favorites WHERE username=%s", (username,))
    favorites = cursor.fetchall()
    cursor.close()
    conn.close()

    # favorites를 딕셔너리로 변환
    fav_list = [{'title': f[1], 'url': f[2], 'summary': f[3], 'id': f[0]} for f in favorites]

    return render_template('favorites.html', favorites=fav_list, username=username)

# 즐겨찾기 삭제 라우트
@app.route('/remove_favorite', methods=['POST'])
def remove_favorite():
    if 'username' not in session:
        flash('로그인 후 이용해주세요.')
        return redirect('/login')

    favorite_id = request.form.get('favorite_id')

    if not favorite_id:
        flash('삭제할 즐겨찾기 ID가 없습니다.')
        return redirect('/favorites')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 해당 즐겨찾기를 삭제
        cursor.execute(
            "DELETE FROM favorites WHERE id = %s AND username = %s",
            (favorite_id, session['username'])
        )
        conn.commit()
        flash('즐겨찾기가 삭제되었습니다.')
    except Exception as e:
        flash('삭제 중 오류가 발생했습니다.')
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('favorites'))

# Flask 앱 실행
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

