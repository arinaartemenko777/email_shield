
from flask import Flask, render_template, request
from flask_cors import CORS
import joblib
from pathlib import Path

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "email_model_real.pkl"
VECTORIZER_PATH = BASE_DIR / "tfidf_vectorizer_real.pkl"

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)




def explain_email(category, subject, message):
    """Izskaidro kategoriju un parāda atrastos vārdus."""

    text = (subject + " " + message).lower()
    reasons = []

    urgent_words = [
        "steidzami", "nekavējoties", "pēc iespējas ātrāk",
        "24 stundu laikā", "šodien", "pēdējais paziņojums",
        "rīkojieties", "last warning", "act now", "hurry up"
    ]

    password_words = [
        "parole", "paroli", "paroles", "pieteikšanās dati",
        "apstipriniet savu identitāti", "apstipriniet savus datus",
        "verifikācija", "verificējiet", "smart-id",
        "password", "verify your identity", "login details"
    ]

    account_words = [
        "konta pārbaude", "konts tiks bloķēts",
        "konta bloķēšana", "konts tiks deaktivizēts",
        "aizdomīga darbība", "neparasta aktivitāte",
        "piekļuve kontam", "konts tiks ierobežots",
        "account will be deactivated", "suspicious activity"
    ]

    link_words = [
        "noklikšķiniet", "spiediet šeit", "atveriet saiti",
        "norādīto saiti", "izmantojiet saiti",
        "click here", "click the button", "provided link"
    ]

    spam_prize_words = [
        "laimējis", "laimējāt", "laimests",
        "esat izvēlēts balvai", "apsveicam",
        "naudas balva", "winner", "you have won",
        "congratulations", "prize"
    ]

    spam_recommendation_words = [
        "ieteiktie produkti", "produktu ieteikumi",
        "piemērotus produktus", "ieteikumi",
        "iepriekš iegādātajām", "jūsu grozā",
        "товар из вашей корзины", "проверьте его до",
        "recommended products", "product recommendations",
        "items in your cart"
    ]

    spam_promotion_words = [
        "piedāvā dažādus produktus",
        "apskatiet visus ieteikumus",
        "īpašām cenām", "atlaides līdz",
        "потрясающими дополнениями",
        "потратьте свыше", "travel with us",
        "путешествуйте с умом",
        "the quality is so buns",
        "skaties garām palaistus",
        "atkārtoti publicēja", "pārpublicēja",
        "here's what's new", "look what you can do now",
        "explore new features", "new features"
    ]

    advertising_words = [
        "atlaide", "atlaidi", "atlaides",
        "atlaižu kods", "kupons", "kuponu",
        "īpašais piedāvājums", "īpaši piedāvājumi",
        "piedāvājums", "piedāvājumi",
        "akcija", "akcijas", "iepērcies",
        "iegādājies", "pērc tagad", "pirkt",
        "pērc biļeti", "biļetes jau pārdošanā",
        "bezmaksas piegāde", "īpašas cenas",
        "reklāmas e-pasti", "jaunumu saņemšanas",
        "saņem līdz pat", "dizaineru zīmolu",
        "pirmajam pasūtījumam", "atlaidi visiem",
        "izpārdošana", "jaunākās funkcijas",
        "pārsteidzošu veiktspēju", "0% procentu līzingu",
        "discount", "discounts", "sale", "flash sale",
        "special offer", "special offers", "offer",
        "offers", "deals", "buy now", "shop now",
        "book now", "save", "promo", "coupon",
        "extra 20% off", "up to", "free delivery",
        "newsletter", "tickets on sale",
        "limited time", "shop our", "purchase now",
        "скидка", "скидки", "акция", "акции",
        "специальные предложения", "предложение",
        "товары со скидкой", "купон", "купите сейчас"
    ]

    def found_words(word_list):
        """Atgriež vārdus, kas tiešām atrasti vēstules tekstā."""
        return list(dict.fromkeys(
            word for word in word_list if word in text
        ))

    def add_reason(description, word_list):
        matches = found_words(word_list)
        if matches:
            reasons.append(
                f"{description} ({', '.join(matches)})."
            )

    if category == "phishing":
        add_reason(
            "E-pastā tiek mudināts rīkoties ātri",
            urgent_words
        )
        add_reason(
            "E-pastā tiek prasīta parole vai pieteikšanās dati",
            password_words
        )
        add_reason(
            "E-pastā minēta aizdomīga darbība vai konta ierobežošana",
            account_words
        )
        add_reason(
            "E-pastā aicina atvērt saiti",
            link_words
        )

    elif category == "spam":
        add_reason(
            "E-pastā tiek solīta balva vai laimests",
            spam_prize_words
        )
        add_reason(
            "E-pastā ir produktu ieteikumi vai preces iepirkumu grozā",
            spam_recommendation_words
        )
        add_reason(
            "E-pastā ir reklāmai līdzīgs saturs",
            spam_promotion_words
        )
        add_reason(
            "E-pastā minētas atlaides vai komerciāli piedāvājumi",
            advertising_words
        )

    elif category == "advertising":
        add_reason(
            "E-pastā reklamē preces, atlaides vai īpašus piedāvājumus",
            advertising_words
        )

    elif category == "normal":
        suspicious_matches = found_words(
            urgent_words + password_words + account_words
        )
        if suspicious_matches:
            reasons.append(
                "Atrastas arī drošības riska frāzes "
                f"({', '.join(suspicious_matches)})."
            )
        else:
            reasons.append(
                "Nav atrastas biežākās steidzamības "
                "vai paroles pieprasījuma pazīmes."
            )

    if not reasons:
        reasons.append(
            "Konkrētas pazīmes no izmantotā vārdu saraksta netika atrastas."
        )

    return reasons



def classify_email(subject, message):
    text = subject + " " + message

    text_tfidf = vectorizer.transform([text])

    prediction = str(model.predict(text_tfidf)[0])

    probabilities = model.predict_proba(text_tfidf)[0]
    classes = model.classes_

    probability_dict = {}

    for class_name, probability in zip(classes, probabilities):
        probability_dict[str(class_name)] = round(
            float(probability * 100), 2
        )

    reasons = explain_email(prediction, subject, message)

    return {
        "prediction": prediction,
        "category": prediction,
        "reasons": reasons,
        "probabilities": probability_dict,
        "phishing_probability": probability_dict.get("phishing", 0),
        "normal_probability": probability_dict.get("normal", 0),
        "spam_probability": probability_dict.get("spam", 0),
        "advertising_probability": probability_dict.get("advertising", 0)
    }


@app.route("/analyze", methods=["POST"])
def analyze_api():
    data = request.get_json(silent=True) or {}

    subject = str(data.get("subject", ""))
    message = str(data.get("message", ""))

    return classify_email(subject, message)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        subject = request.form.get("subject", "")
        message = request.form.get("message", "")

        result = classify_email(subject, message)

    return render_template("index.html", result=result)


if __name__ == "__main__":
    print("==============================")
    print("Latvian Email Security")
    print("==============================")
    print("Serveris darbojas: http://127.0.0.1:5000")
    print("Kategorijas:", model.classes_)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
