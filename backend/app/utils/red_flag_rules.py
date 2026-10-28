"""
Red-flag rules for the emergency detector.

Every pattern here is matched against text produced by clinical_text.normalize():
lowercase, apostrophes removed ("can't" -> "cant"), punctuation removed.
So write patterns WITHOUT apostrophes.

Design rule: when unsure, a rule should fire. A false alarm shows a safety
message; a missed emergency can cost a life.

Each rule: (rule_id, category, regex)
"""

import re

# Categories (used to choose the right first-aid text in emergency_agent)
CARDIAC = "CARDIAC"
BREATHING = "BREATHING"
STROKE = "STROKE"
BLEEDING = "BLEEDING"
CONSCIOUSNESS = "CONSCIOUSNESS"
SEIZURE = "SEIZURE"
CHOKING = "CHOKING"
POISONING = "POISONING"
ALLERGIC = "ALLERGIC"
SELF_HARM = "SELF_HARM"
GENERAL = "GENERAL"

# Categories where "I don't want to die" style denials must NOT silence the alert
# and where the 'informational question' exemption never applies.
NEVER_SUPPRESS = {SELF_HARM}

_NOT_NOSE = r"(?!\s+(?:through|via|from|out of)\s+(?:my\s+|the\s+|both\s+|one\s+)?(?:nose|nostrils?))"

_RAW_RULES = [
    # ---------------- CARDIAC ----------------
    ("chest_pain", CARDIAC, r"\bchest (?:pain|pains|tightness|pressure|heaviness|discomfort|burning)\b"),
    ("pain_in_chest", CARDIAC, r"\b(?:pain|pressure|tightness|heaviness|squeezing) (?:in|across|on) (?:my |the |his |her |their )?chest\b"),
    ("chest_tight", CARDIAC, r"\bchest (?:feels?|is|was|feeling) (?:very |so |really )?(?:tight|heavy|crushed|squeezed|on fire)\b"),
    ("crushing_chest", CARDIAC, r"\b(?:crushing|squeezing|stabbing) chest\b|\belephant on my chest\b"),
    ("heart_attack", CARDIAC, r"\bheart attack\b"),
    ("cardiac_arrest", CARDIAC, r"\b(?:cardiac arrest|heart stopped|heart has stopped|no pulse)\b"),
    ("heart_hurting", CARDIAC, r"\b(?:heart|dil) (?:is |was )?(?:hurting|paining)\b"),
    ("arm_jaw_pain", CARDIAC, r"\bpain (?:spreading|radiating|going|shooting) (?:to|down) (?:my |the |his |her )?(?:left )?(?:arm|jaw|shoulder)\b"),
    ("seene_dard", CARDIAC, r"\b(?:seene|seeney|chhati|chaati|chest) (?:mein|me|main) (?:dard|pain|jalan|bhaari|bhari)\b"),
    ("dil_ka_daura", CARDIAC, r"\bdil ka daura\b"),
    ("hi_chest_pain", CARDIAC, r"(?:सीने|छाती) (?:में|मे) (?:दर्द|जलन|भारीपन)|दिल का दौरा"),

    # ---------------- BREATHING ----------------
    ("cant_breathe", BREATHING, r"\b(?:cant|cannot|can not|couldnt|unable to|not able to) (?:breathe|breath)\b" + _NOT_NOSE),
    ("cant_catch_breath", BREATHING, r"\b(?:cant|cannot|couldnt) (?:catch|get) (?:my |a )?breath\b"),
    ("cant_get_air", BREATHING, r"\b(?:cant|cannot|couldnt) get (?:any |enough )?(?:air|oxygen)\b"),
    ("difficulty_breathing", BREATHING, r"\b(?:difficulty|trouble|struggling|struggle|hard|hardly able|labou?red) (?:to )?(?:in )?(?:breathing|breathe|breath)\b" + _NOT_NOSE),
    ("short_of_breath", BREATHING, r"\b(?:shortness of breath|short of breath|breathless(?:ness)?|gasping|gasp for (?:air|breath))\b"),
    ("not_breathing", BREATHING, r"\b(?:not|stopped|stops|isnt|barely) breathing\b"),
    ("blue_lips", BREATHING, r"\b(?:lips|face|fingers|nails) (?:are |is |turning |turned |going |look(?:s|ing)? )?(?:blue|bluish)\b"),
    ("saans_nahi", BREATHING, r"\bsaans (?:nahi|nahin|nhi) (?:aa|a|le|lia|liya)|\bsaans lene (?:mein|me|main) (?:takleef|dikkat|problem|taklif)\b"),
    ("hi_breathing", BREATHING, r"(?:सांस|साँस) (?:नहीं|लेने में)"),

    # ---------------- STROKE ----------------
    ("stroke", STROKE, r"(?<!\bback )(?<!\bbreast )(?<!\bkey )(?<!\bbrush )(?<!\bmaster )\bstrokes?\b(?!\s+of\s+(?:luck|genius))"),
    ("face_droop", STROKE, r"\b(?:face|mouth|smile) (?:is |was |has |started )?(?:drooping|droop|drooped|dropping|crooked|lopsided|uneven)\b"),
    ("one_side", STROKE, r"\b(?:one side|half) of (?:my |the |his |her )?(?:face|body)\b.{0,25}\b(?:numb|weak|paralys\w*|drooping|cant move)"),
    ("sudden_weakness", STROKE, r"\bsudden(?:ly)? (?:weakness|numbness|paralysis|loss of (?:vision|balance|speech)|confusion|trouble (?:speaking|seeing|walking))\b"),
    ("limb_sudden", STROKE, r"\b(?:arm|leg|hand) suddenly (?:went|became|is|feels?) (?:weak|numb|limp|dead)\b"),
    ("slurred", STROKE, r"\b(?:slurred speech|slurring|speech is slurred|talking funny)\b"),
    ("cant_speak", STROKE, r"\b(?:unable to|not able to) (?:speak|talk)\b|\bsuddenly (?:cant|cannot) (?:speak|talk)\b|\b(?:cant|cannot) (?:speak|talk) (?:properly|normally|at all|suddenly)\b"),
    ("severe_confusion", STROKE, r"\bsevere(?:ly)? confus(?:ed|ion)\b"),
    ("worst_headache", STROKE, r"\bworst headache (?:of|in) (?:my|his|her|their) life\b|\bthunderclap headache\b|\bsudden (?:severe|terrible|worst|intense|excruciating) headache\b"),

    # ---------------- BLEEDING ----------------
    ("severe_bleeding", BLEEDING, r"\b(?:severe|heavy|massive|major|serious|uncontrolled|excessive) bleeding\b"),
    ("bleeding_heavily", BLEEDING, r"\bbleeding (?:heavily|profusely|badly|a lot|too much|everywhere|nonstop|non stop)\b"),
    ("wont_stop_bleeding", BLEEDING, r"\b(?:bleeding|blood) (?:wont|will not|doesnt|does not|cant be) (?:stop|be stopped)\b|\bwont stop bleeding\b"),
    ("blood_everywhere", BLEEDING, r"\b(?:lot of blood|lots of blood|blood everywhere|soaked in blood|pool of blood|losing (?:a lot of )?blood)\b"),
    ("major_injury", BLEEDING, r"\b(?:major|serious|severe) (?:injury|accident|trauma|head injury)\b|\bhit (?:my|his|her) head (?:hard|badly)\b"),
    ("pregnancy_bleeding", BLEEDING, r"\b(?:pregnant|pregnancy)\b.{0,30}\b(?:heavy bleeding|bleeding heavily|severe pain)\b|\bheavy bleeding\b.{0,30}\b(?:pregnant|pregnancy)\b"),

    # ---------------- CONSCIOUSNESS ----------------
    ("unconscious", CONSCIOUSNESS, r"\b(?:unconscious|unresponsive|collapsed|passed out|blacked out|fainted|fainting|behosh|behoshi)\b"),
    ("not_waking", CONSCIOUSNESS, r"\b(?:not|wont|will not|cant be|cannot be|doesnt|does not|isnt) (?:waking|wake|woken|responding|respond)\b"),
    ("hi_unconscious", CONSCIOUSNESS, r"बेहोश"),

    # ---------------- SEIZURE ----------------
    ("seizure", SEIZURE, r"\b(?:seizure|seizures|seizing|convulsion|convulsions|convulsing|epileptic fit|having a fit|mirgi)\b"),

    # ---------------- CHOKING ----------------
    ("choking", CHOKING, r"\b(?:choking|choked|stuck in (?:my|his|her|the) (?:throat|windpipe))\b"),

    # ---------------- POISONING / OVERDOSE ----------------
    ("overdose", POISONING, r"\b(?:overdose|overdosed|overdosing)\b|\btook too (?:many|much) (?:of )?(?:my |the |his |her )?(?:pills|tablets|capsules|medicine|medication|meds|painkillers|paracetamol|crocin|dolo|sleeping pills|insulin|aspirin|ibuprofen)\b|\btook (?:\d+|ten|twenty|thirty|many|all (?:my|the|of)) (?:pills|tablets|capsules|painkillers|sleeping pills)\b"),
    ("poisoned", POISONING, r"\b(?:poisoned|swallowed (?:poison|bleach|acid|pesticide|phenyl|kerosene|petrol|detergent|battery)|drank (?:poison|bleach|acid|pesticide|phenyl|kerosene|petrol)|ate (?:poison|rat poison)|rat poison|consumed (?:poison|pesticide|phenyl))\b"),

    # ---------------- ALLERGIC ----------------
    ("anaphylaxis", ALLERGIC, r"\b(?:anaphylaxis|anaphylactic|throat (?:is |feels? |getting )?(?:closing|closed|swelling shut)|tongue (?:is )?swelling)\b"),

    # ---------------- GENERAL ----------------
    ("think_dying", GENERAL, r"\b(?:think|feel|feels|thinks) (?:im|i am|he is|she is|hes|shes|they are|theyre) (?:dying|going to die)\b|\bam i dying\b"),

    # ---------------- SELF-HARM ----------------
    ("suicide", SELF_HARM, r"\b(?:suicide|suicidal|suicidality)\b"),
    ("kill_myself", SELF_HARM, r"\b(?:kill|killing|hang|hanging|drown|drowning|shoot|shooting|stab|stabbing|poison|poisoning|end|ending) (?:myself|my self|my own life|my life)\b"),
    ("want_to_die", SELF_HARM, r"\b(?:want|wanna|wish|wished|plan|planning|thinking of|thinking about|ready|decided) (?:to |i could |i would |i was )?(?:die|be dead|disappear forever|not wake up|not be alive)\b"),
    ("dont_want_live", SELF_HARM, r"\b(?:dont|do not|no longer|not) want(?:ing)? to (?:live|be alive|exist)\b|\bno (?:reason|point) (?:to|in) (?:live|living|go on|going on|being alive)\b|\blife (?:is|isnt|is not) (?:not )?worth (?:living|it)\b|\bbetter off (?:dead|without me)\b|\beveryone (?:would be )?better off without me\b"),
    ("end_it_all", SELF_HARM, r"\bend (?:it all|everything|my suffering)\b|\btake my own life\b|\bgive up on life\b|\bgoing to end it\b"),
    ("self_harm", SELF_HARM, r"\bself harm(?:ing)?\b|\bslit (?:my )?wrists?\b|\bcut (?:my )?wrists?\b|\bjump(?:ing)? (?:off|from) (?:a |the |my )?(?:bridge|building|roof|terrace|balcony|train|cliff)\b"),
    ("self_harm_intent", SELF_HARM, r"\b(?:want|wanna|going|planning|plan|thinking of|thinking about|thought about|urge|urges|feel like|tempted|trying|tried|keep|keeps|started) (?:to )?(?:hurt|hurting|harm|harming|cut|cutting|injure|injuring|punish|punishing) (?:myself|my self)\b|\b(?:hurt|hurting|harm|harming|cut|cutting) myself on purpose\b"),
    ("hinglish_self_harm", SELF_HARM, r"\b(?:marna chah\w*|mar jana chah\w*|mar jaana chah\w*|jaan de dunga|jaan de dungi|khudkushi|khud kushi|aatmahatya|atmahatya|suicide karna|jeena nahi|jeene ka mann nahi|jeene ka man nahi)\b|\bmar (?:jaun|jaaun|jau)\b"),
    ("hi_self_harm", SELF_HARM, r"आत्महत्या|खुदकुशी|मरना चाह|जीना नहीं|जीने का मन नहीं|जान दे"),
]

RULES = [(rule_id, category, re.compile(pattern, re.IGNORECASE)) for rule_id, category, pattern in _RAW_RULES]


# --------------------------------------------------
# Negation cues. If one of these sits within NEGATION_WINDOW tokens before a
# match (with no comma / "and" between), the match is treated as a denial.
# NOTE: "cant" / "cannot" are deliberately NOT here -- "cant breathe" is a symptom.
# --------------------------------------------------
NEGATION_CUES = {
    "no", "not", "dont", "doesnt", "didnt", "never", "without", "nor",
    "isnt", "arent", "wasnt", "werent", "havent", "hasnt", "hadnt", "wont",
    "denies", "denied", "deny", "negative", "nothing", "none", "neither",
    "free", "ruled",
}
NEGATION_WINDOW = 4
# Self-harm statements get a much tighter window: "not sure if I want to die"
# must NOT be silenced by the "not" four words earlier. Only an adjacent
# denial ("dont want to die", "never kill myself") counts.
SELF_HARM_NEGATION_WINDOW = 2

# Tokens that end a negation's reach even inside one clause.
SCOPE_BREAKERS = {",", "and", "then", "also", "plus", "now", "later", "still"}

# A clause beginning like this is an information question, not a report.
INFO_QUESTION_START = re.compile(
    r"^(?:what|whats|which|why|how|when|can you explain|explain|tell me about|define|difference between)\b"
)
INFO_QUESTION_CONTENT = re.compile(
    r"\b(?:symptoms? of|signs? of|causes? of|cause of|risk factors?|prevent(?:ion)?|how to (?:prevent|avoid|recognise|recognize|spot)|"
    r"what is|what are|meaning of|mean|definition|difference between|treatment for|first aid for)\b"
)
# If any of these appear, the person is probably describing a real situation.
PERSONAL_CUES = re.compile(
    r"\b(?:right now|just now|currently|having|since (?:morning|yesterday|last night|today)|suddenly)\b"
    r"|\b(?:i|he|she|they|hes|shes|im|ive|my \w+|someone|somebody) (?:have|has|had|am|is|are|feel|feels|felt|got|gets|got)\b"
)
