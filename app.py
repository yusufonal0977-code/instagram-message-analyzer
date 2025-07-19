import os
import secrets
import string
import random
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv() # .env dosyasını en başta yükle

# your_analysis_script.py'den importlar
from your_analysis_script import analyze_messages_by_category_score_no_stemming, all_keywords_categories

app = Flask(__name__)
# SECRET_KEY'i .env'den çek, yoksa varsayılan bir değer kullan (güvenlik için üretimde varsayılan kullanılmamalı)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_secret_fallback_key_here') 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# E-posta kullanıcı adı ve şifresini .env'den çek
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
# Varsayılan göndericiyi .env'deki kullanıcı adından al
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

db = SQLAlchemy(app)
mail = Mail(app)

# Veritabanı modeli
class Verification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(6), nullable=False)
    filepaths = db.Column(db.String(1000), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

# Doğrulama kodu oluşturma fonksiyonu
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

# Doğrulama e-postası gönderme fonksiyonu
def send_verification_email(recipient_email, code):
    msg = Message('Instagram Mesaj Analizi - Doğrulama Kodunuz',
                  sender=app.config['MAIL_DEFAULT_SENDER'], # Sender belirtildi
                  recipients=[recipient_email])
    msg.body = f"Merhaba,\n\nInstagram Mesaj Analizi hizmetimiz için doğrulama kodunuz: {code}\n\nLütfen bu kodu web sitesindeki ilgili alana giriniz.\n\nSaygılarımızla,\nInstagram Mesaj Analizi Ekibi"
    try:
        mail.send(msg)
        print(f"Doğrulama e-postası '{recipient_email}' adresine gönderildi.")
        return True
    except Exception as e:
        print(f"Doğrulama e-postası gönderme hatası: {e}")
        return False

# Analiz sonuçlarını e-posta ile gönderme fonksiyonu
def send_analysis_results_email(recipient_email, results):
    msg = Message('Instagram Mesaj Analizi - Sonuçlarınız Hazır!',
                  sender=app.config['MAIL_DEFAULT_SENDER'], # Sender belirtildi
                  recipients=[recipient_email])

    html_body = "<h1>Instagram Mesaj Analizi Sonuçlarınız</h1>"
    html_body += "<p>Aşağıda mesajlarınızın kategori bazında analiz sonuçları bulunmaktadır. Puanlar, ilgili kategorideki kelimelerin toplam kelime sayısına oranını bin ile çarparak elde edilmiştir.</p>"
    for user, categories in results.items():
        html_body += f"<h2>'{user}' Kullanıcısı İçin Analiz:</h2><table border='1' cellpadding='5' cellspacing='0'><thead><tr><th>Kategori</th><th>Puan (x1000)</th></tr></thead><tbody>"
        for category, score in categories.items():
            html_body += f"<tr><td>{category.capitalize()}</td><td>{score:.2f}</td></tr>"
        html_body += "</tbody></table><br>"

    html_body += "<p>Umarız bu analiz faydalı olmuştur. Herhangi bir sorunuz olursa bizimle iletişime geçmekten çekinmeyin.</p>"
    html_body += "<p>Saygılarımızla,<br>Instagram Mesaj Analizi Ekibi</p>"

    msg.html = html_body

    try:
        mail.send(msg)
        print(f"Analiz sonuçları e-postası '{recipient_email}' adresine gönderildi.")
        return True
    except Exception as e:
        print(f"Sonuç e-postası gönderme hatası: {e}")
        return False

# Ana sayfa (dosya yükleme ve e-posta girişi)
@app.route('/')
def index():
    return render_template('index.html')

# Dosya yükleme ve doğrulama e-postası gönderme rotası
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({"error": "Dosya yüklenmedi"}), 400

    uploaded_files = request.files.getlist('files[]')
    user_email = request.form.get('email')

    if not user_email:
        return jsonify({"error": "E-posta adresi gerekli"}), 400

    if not uploaded_files or all(f.filename == '' for f in uploaded_files):
        return jsonify({"error": "Dosya seçilmedi"}), 400

    temp_dir = 'temp_uploads'
    os.makedirs(temp_dir, exist_ok=True)

    file_paths = []
    for file in uploaded_files:
        if file.filename == '':
            continue
        if file and file.filename.endswith('.json'):
            filepath = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(filepath)
            file_paths.append(filepath)

    if not file_paths:
        # Eğer temp_dir boşsa sil
        if not os.listdir(temp_dir):
            os.rmdir(temp_dir)
        return jsonify({"error": "Geçerli JSON dosyası bulunamadı."}), 400

    verification_code = generate_verification_code()

    existing_verification = Verification.query.filter_by(email=user_email).first()
    if existing_verification:
        existing_verification.code = verification_code
        existing_verification.filepaths = json.dumps(file_paths)
        existing_verification.is_verified = False
    else:
        new_verification = Verification(email=user_email, code=verification_code, filepaths=json.dumps(file_paths))
        db.session.add(new_verification)
    db.session.commit()

    if send_verification_email(user_email, verification_code):
        session['user_email_for_verification'] = user_email # Oturuma e-postayı kaydet
        return jsonify({
            "message": "Doğrulama kodu e-posta adresinize gönderildi. Lütfen gelen kutunuzu kontrol edin.",
            "redirect_to": url_for('verify_email') # Doğrulama sayfasına yönlendir
        }), 200
    else:
        # E-posta gönderme başarısız olursa veritabanı kaydını geri al/sil ve dosyaları temizle
        if existing_verification:
            db.session.rollback() # Değişiklikleri geri al
        else:
            db.session.delete(new_verification) # Yeni oluşturulanı sil
        db.session.commit()
        # Yüklenen geçici dosyaları da sil
        for fp in file_paths:
            if os.path.exists(fp):
                os.remove(fp)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

        return jsonify({"error": "Doğrulama e-postası gönderilemedi. Lütfen e-posta adresinizi kontrol edin veya daha sonra tekrar deneyin."}), 500

# E-posta doğrulama ve analiz başlatma rotası
@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        user_email = session.get('user_email_for_verification')
        if not user_email:
            return jsonify({"error": "E-posta adresi oturumda bulunamadı. Lütfen tekrar dosya yükleyin."}), 400

        entered_code = request.form.get('code')
        
        # Doğrulama kodunu ve doğrulanmamış durumu kontrol et
        verification_entry = Verification.query.filter_by(email=user_email, code=entered_code, is_verified=False).first()

        if verification_entry:
            verification_entry.is_verified = True
            db.session.commit()

            file_paths = json.loads(verification_entry.filepaths)
            
            try:
                # Analiz fonksiyonunu çağır
                normalized_scores = analyze_messages_by_category_score_no_stemming(file_paths, all_keywords_categories)
                
                # Terminale yazdırma eklentisi (İstenen çıktı)
                print("\n--- Analiz Sonuçları (Terminal Çıktısı) ---")
                for user, categories in normalized_scores.items():
                    print(f"Kullanıcı: {user}")
                    for category, score in categories.items():
                        print(f"  {category.capitalize()}: {score:.2f} (x1000)")
                print("-------------------------------------------\n")

                # Analiz sonuçlarını e-posta ile gönder
                send_analysis_results_email(user_email, normalized_scores)

                # Geçici dosyaları sil
                for fp in file_paths:
                    if os.path.exists(fp):
                        os.remove(fp)
                # temp_uploads klasörü boşsa sil
                temp_dir = os.path.dirname(file_paths[0]) if file_paths else 'temp_uploads'
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)

                # Veritabanı kaydını sil
                db.session.delete(verification_entry)
                db.session.commit()

                session.pop('user_email_for_verification', None) # Oturumdaki e-postayı temizle
                
                # Yeni "Analiz Başlatıldı" sayfasına yönlendirme yap
                return render_template('analysis_started.html') 
            except Exception as e:
                # Analiz veya e-posta gönderme sırasında hata olursa dosyaları ve kaydı temizle
                print(f"Analiz veya sonuç e-postası gönderme hatası: {e}")
                for fp in file_paths:
                    if os.path.exists(fp):
                        os.remove(fp)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
                db.session.delete(verification_entry)
                db.session.commit()
                return jsonify({"error": "Analiz sırasında bir hata oluştu veya sonuçlar gönderilemedi. Lütfen daha sonra tekrar deneyin."}), 500

        else:
            return jsonify({"error": "Yanlış veya süresi dolmuş doğrulama kodu. Lütfen kontrol edin."}), 400
    
    # GET isteği için doğrulama HTML'ini göster
    return render_template('verify_email.html')

# Uygulama başlatıldığında veritabanını oluştur (sadece ilk çalıştırmada veya değişimde)
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Veritabanı tablolarını oluştur
    app.run(debug=True) # Hata ayıklama modunda çalıştır