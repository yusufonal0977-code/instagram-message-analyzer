import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import defaultdict
import json
import os

# NLTK kaynaklarını indir (sadece bir kere çalıştırılması yeterlidir)
# import ssl
# try:
#     _create_unverified_https_context = ssl._create_unverified_context
# except AttributeError:
#     pass
# else:
#     ssl._create_unverified_https_context = _create_unverified_https_context

# try:
#     nltk.data.find('corpora/stopwords')
# except nltk.downloader.DownloadError:
#     nltk.download('stopwords')
# try:
#     nltk.data.find('tokenizers/punkt')
# except nltk.downloader.DownloadError:
#     nltk.download('punkt')


# Türkçe stopwords (durma kelimeleri) listesi
# Bu liste geniş tutulmaya devam etmeli ki gereksiz kelimeler elensin
TR_STOPWORDS = set(stopwords.words('turkish'))
TR_STOPWORDS.update([
    'bir', 'biraz', 'çok', 'daha', 'ki', 'da', 'de', 'ise', 'mi', 'mı', 'mu', 'mü', 'bu', 'o', 'şu', 'biz', 'siz', 'onlar',
    'birşey', 'şey', 'benim', 'senin', 'onun', 'bana', 'sana', 'ona', 'bize', 'size', 'onlara', 'beni', 'seni', 'onu',
    'bizi', 'sizi', 'onları', 'benimle', 'seninle', 'onunla', 'bizimle', 'sizinle', 'onlarla', 'ile', 'gibi', 'için',
    'göre', 'kadar', 'tarafından', 'üzerine', 'altına', 'içine', 'dışına', 'sonra', 'önce', 'ama', 'fakat', 'ancak',
    'lakin', 'oysa', 'halbu ki', 've', 'ile', 'ya da', 'yahut', 'bile', 'de', 'ise de', 'zira', 'çünkü', 'oysaki',
    'meğer', 'belki', 'herhalde', 'gerçi', 'şüphesiz', 'kesinlikle', 'mutlaka', 'galiba', 'elbette', 'sözde',
    'aslında', 'yani', 'nitekim', 'kısaca', 'özetle', 'mesela', 'örneğin', 'hele', 'ayrıca', 'üstelik', 'böylece',
    'öyleyse', 'işte', 'demek ki', 'halbuki', 'hem', 'hem de', 'ne', 'ne de', 'ya', 'ya da', 'ister', 'isterse',
    'gerek', 'gerekse', 'madem', 'mademki', 'şayet', 'eğer', 'olursa', 'olmazsa', 'diye', 'değil', 'yok', 'var',
    'en', 'az', 'çok', 'tek', 'ilk', 'son', 'büyük', 'küçük', 'eski', 'yeni', 'iyi', 'kötü', 'güzel', 'çirkin',
    'geniş', 'dar', 'uzun', 'kısa', 'hızlı', 'yavaş', 'kolay', 'zor', 'doğru', 'yanlış', 'şimdi', 'sonra', 'dün',
    'bugün', 'yarın', 'burada', 'orada', 'şurada', 'nerede', 'niçin', 'neden', 'nasıl', 'ne zaman', 'kim', 'ne',
    'hangi', 'kaç', 'nereye', 'nereden', 'kime', 'kimden', 'kimin', 'kime', 'kimlere', 'sizler', 'bizler', 'onlar',
    'sizden', 'bizden', 'onlardan', 'senden', 'benden', 'ondan', 'kimse', 'hiçbir', 'bazı', 'tüm', 'bütün', 'her',
    'herkes', 'kimisi', 'pek', 'çokça', 'epey', 'epeyce', 'oldukça', 'epeyce', 'hayli', 'olur', 'tamam', 'peki', 'evet', 'hayır'
])


def clean_text(text):
    """Metni küçük harfe çevirir, noktalama işaretlerini kaldırır, boşlukları düzenler ve durma kelimelerini çıkarır."""
    text = text.lower() # Küçük harfe çevir
    text = text.translate(str.maketrans('', '', string.punctuation)) # Noktalama işaretlerini kaldır
    text = re.sub(r'\s+', ' ', text).strip() # Birden fazla boşluğu tek boşluğa çevir

    words = word_tokenize(text, language='turkish') # Kelimelere ayır (Türkçe desteğiyle)
    filtered_words = [word for word in words if word not in TR_STOPWORDS] # Durma kelimelerini çıkar

    return " ".join(filtered_words) # Temizlenmiş metni geri döndür

# ** Anahtar Kelime Kategorileri (Daraltılmış ve Kesin Kelimeler) **
all_keywords_categories = {
    "manipülatif": [
        "yüzünden", "senin yüzünden", "suçlu", "suçlusun", "haksızsın", "mecbur", 
        "zorundasın", "tehdit", "şantaj", "kandır", "yalan", "aldattın", "kıskanç",
        "mağdur", "bencil", "benim suçum", "pişman", "pişman olursun", "bitirdin", 
        "mahvettin", "acıttın", "benimle alay", "küçük düşürdün", "beni üzüyorsun",
        "umurumda değil", "fark etmez", "sen bilirsin", "sana kalmış", "beni bıraktın",
        "yalnız bıraktın", "suç senin", "hep aynı", "seni tanıyamıyorum", "değiştin", 
        "beni sevmiyorsun", "değer vermiyorsun", "her şeyi mahvettin", "anlayamıyorsun",
        "fedakarlık yaptım", "bunu beklemezdim", "yakışmadı", "ne anlarsın", "boşuna",
        "vazgeçtim", "pes ettim", "hak etmiyorsun", "yetmedim", "hasta oldum", "bunları yaşattın",
        "hak etmedim", "neden böyle", "beni mi deniyorsun", "cezalandırıyorsun", "sevmek zorunda",
        "düşünmüyorsun", "kaybetmekten korkmuyorsun", "kışkırtıyorsun", "çıldırtıyorsun", 
        "affetmeyeceğim", "nefret ediyorum", "tükettin", "ahım var", "hesabını sorarım", "sana göstereceğim",
        "dersini alırsın", "acırım sana", "yazık", "mahvedeceğim", "rezil ettin", "aşağıladın", 
        "gururumla oynadın", "affedemem", "bitti", "işim bitti", "ayrılalım", "boşanalım", "dayanamıyorum",
        "benden uzak", "rahat bırak", "konuşma", "yazıklar olsun", "görmedim", "seçmemeliydim", 
        "keşke tanımasaydım", "canım yanıyor", "kalbim acıyor", "bunu bana nasıl", "perişan ettin", 
        "sonumu getirdin", "başım belaya", "mutsuzum", "ağlıyorum", "bu duruma sen", "benden bu kadar",
        "artık yeter", "seninle yapamıyorum"
    ],
    "romantik": [
        "aşkım", "sevgilim", "canım", "hayatım", "bitanem", "seni seviyorum",
        "kalbim", "gülüm", "meleğim", "ruhum", "özledim", "seninle", "birlikte",
        "her şeyim", "gözlerin", "ellerin", "kalbimdesin", "sonsuza kadar",
        "rüya gibi", "tutku", "aşk", "sevgili", "biricik", "mucizem", "duam", 
        "tek aşkım", "mutluluğum", "cennetim", "dünyam", "değerlim", "sevdiceğim",
        "sevdam", "gönlüm", "kalbimin sesi", "ruheşim", "ikimiz", "hayat arkadaşım",
        "can yoldaşım", "ömürlük", "sana aşığım", "sensiz olmaz", "yüreğim"
    ],
    "eğlenceli": [
        "haha", "hahaha", "xD", "komik", "güldüm", "şaka", "mizah", "eğlenceli",
        "kahkaha", "çılgın", "süper", "harika", "müthiş", "neşe", "keyif", "neşeli",
        "gülmek", "şakalar", "güldürdün", "eğlendik", "espri", "komedyen",
        "neşeli haller", "pozitif", "gülüş", "eğlenmek", "keyifli", "şen", "coşku",
        "enerjik", "canlı", "mutlu", "fantastik", "olağanüstü", "şahane", "mükemmel"
    ],
    "sakin": [
        "tamam", "olur", "peki", "sakin ol", "rahatla", "anladım", "merak etme",
        "iyiyim", "düşünelim", "bekle", "acele etme", "sorun yok", "hallederiz",
        "sıkıntı yok", "rahatım", "nefes al", "gevşe", "endişelenme", "telaşlanma",
        "dingin", "huzurlu", "sessiz", "barış", "sabırlı ol", "umursama", "boşver",
        "huzur", "sükunet", "yavaşla", "kontrol altında", "her şey yolunda", 
        "problem yok", "kafan rahat", "sakinleş", "dert etme", "soğukkanlı", "bırak gitsin",
        "kafana takma"
    ],
    "duygusal": [
        "üzgünüm", "mutsuzum", "kötü hissediyorum", "ağlamak istiyorum", "yalnızım",
        "depresif", "kırgınım", "incindim", "zor zamanlar", "çaresizim", "üzüldüm",
        "hayal kırıklığı", "kalbim acıyor", "düşünceliyim", "hissediyorum", "yorgunum",
        "bitkinim", "bunalım", "dertli", "hüzünlü", "kederli", "gözyaşı", "pişmanım",
        "ruh halim", "karmaşık duygular", "derin", "hassas", "umutsuzluk", "kayıp",
        "hasret", "özlem", "keder", "dayanamıyorum", "gücüm kalmadı", "bitmişim",
        "ağlıyorum", "kalbim parçalandı", "endişe", "panik", "tedirgin", "korkunç",
        "karanlık", "kaybolmuş", "bıktım", "usandım", "canım sıkkın", "perişan",
        "mahvolmuş", "acı", "kalbim kanıyor", "hıçkırık", "yalvarış", "tükendim",
        "ölmek istiyorum", "yaşamak istemiyorum", "anlamsız", "gülmek gelmiyor", 
        "hüzünlü", "kalbim duracak", "nefes alamıyorum", "geçmiyor", "unutamıyorum",
        "yara", "iyileşmez", "boğuluyorum", "çıkış yok", "son", "bitiş", "umudum kalmadı",
        "psikolojim bozuk", "moralsizim", "içime kapandım"
    ]
}


def analyze_messages_by_category_score_no_stemming(json_file_paths, all_keywords_to_track):
    """
    Birden fazla Instagram mesaj JSON dosyasını analiz eder ve her kategorideki
    anahtar kelimelerin kullanımını puanlama sistemiyle değerlendirir.
    Stemming yapılmaz, anahtar kelime listeleri olduğu gibi kullanılır.

    Args:
        json_file_paths (list): Instagram mesaj JSON dosyalarının yollarını içeren bir liste.
        all_keywords_to_track (dict): Kategori adlarını anahtar, anahtar kelime listelerini değer
                                      olarak içeren bir sözlük. Kelimeler küçük harfe çevrilmiş olmalı.

    Returns:
        dict: Her kişi için her kategoriye ait normalleştirilmiş skorları içeren bir sözlük.
    """
    user_category_scores = defaultdict(lambda: defaultdict(float))
    user_total_word_counts = defaultdict(int)

    for json_file_path in json_file_paths:
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            # print(f"Hata: Dosya bulunamadı - '{os.path.basename(json_file_path)}'. Bu dosya atlanıyor.")
            continue
        except json.JSONDecodeError:
            # print(f"Hata: JSON dosyası geçersiz - '{os.path.basename(json_file_path)}'. Bu dosya atlanıyor.")
            continue
        except Exception as e:
            # print(f"Beklenmeyen bir hata oluştu '{os.path.basename(json_file_path)}' okunurken: {e}. Bu dosya atlanıyor.")
            continue

        if 'messages' in data and isinstance(data['messages'], list):
            for message in data['messages']:
                sender = message.get('sender_name', 'Bilinmeyen')
                content = message.get('content', '')

                cleaned_content = clean_text(content)
                content_words = cleaned_content.split()
                user_total_word_counts[sender] += len(content_words)

                for category, keywords_list in all_keywords_to_track.items():
                    for keyword in keywords_list:
                        # Tam kelime eşleşmesi için \b (word boundary) kullanılıyor
                        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', cleaned_content))
                        user_category_scores[sender][category] += count
        else:
            pass # print uyarılarını kaldırdık, temiz çıktı için

    normalized_scores = defaultdict(lambda: defaultdict(float))
    for user, categories_data in user_category_scores.items():
        total_words = user_total_word_counts[user]
        if total_words > 0:
            for category, score in categories_data.items():
                normalized_scores[user][category] = (score / total_words) * 1000
        else:
            for category in categories_data.keys():
                normalized_scores[user][category] = 0.0

    return normalized_scores