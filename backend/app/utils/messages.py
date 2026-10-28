"""
Fixed, pre-written user-facing messages for the care-navigation workflow and
for emergency replies, in English (en), Hindi (hi), Marathi (mr) and Hinglish.

Why fixed text instead of an LLM: these messages must be instant, identical,
and must not invent anything about hospitals or bookings.

NOTE: the Hindi and Marathi wording was written by an AI model and has NOT been
reviewed by a native speaker or a clinician. Have both review it before real use.
Languages without an entry here fall back to English.
"""

from typing import Optional

M = {
    # ---------- emergency (used by emergency_agent for non-English replies) ----------
    "emergency_call": {
        "en": "This could be a medical emergency. Please call 112 (India's national emergency number) right now, or 108 for an ambulance in most states. If someone is with you, ask them to stay with you and help. Don't wait to see if it passes, and avoid driving yourself.",
        "hinglish": "Yeh medical emergency ho sakti hai. Kripya abhi 112 (India ka national emergency number) par call karein, ya zyadatar rajyon mein ambulance ke liye 108. Agar koi aapke saath hai to usse paas rehne aur madad karne ko kahein. Intezaar na karein ki yeh theek ho jaye, aur khud gaadi na chalayein.",
        "hi": "यह एक मेडिकल इमरजेंसी हो सकती है। कृपया अभी 112 (भारत का राष्ट्रीय आपातकालीन नंबर) पर कॉल करें, या ज़्यादातर राज्यों में एम्बुलेंस के लिए 108 पर। अगर कोई आपके साथ है तो उससे पास रहने और मदद करने को कहें। यह देखने के लिए इंतज़ार न करें कि अपने आप ठीक होता है या नहीं, और खुद गाड़ी न चलाएँ।",
        "mr": "ही वैद्यकीय आणीबाणी असू शकते. कृपया आत्ताच 112 (भारताचा राष्ट्रीय आणीबाणी क्रमांक) वर कॉल करा, किंवा बहुतेक राज्यांत रुग्णवाहिकेसाठी 108 वर. कोणी तुमच्यासोबत असेल तर त्यांना जवळ राहून मदत करायला सांगा. आपोआप बरे होते का हे पाहण्यासाठी थांबू नका आणि स्वतः गाडी चालवू नका.",
    },
    "emergency_wait": {
        "en": "",
        "hinglish": "Madad aane tak: shaant rahein, baithein ya letein, khane-peene ki koi cheez ya dawai na lein jab tak emergency operator na bole, aur kisi ko apne paas rakhein.",
        "hi": "मदद आने तक: शांत रहें, बैठें या लेटें, जब तक इमरजेंसी ऑपरेटर न कहे तब तक कुछ खाएँ-पिएँ या दवा न लें, और किसी को अपने पास रखें।",
        "mr": "मदत येईपर्यंत: शांत रहा, बसा किंवा झोपा, आणीबाणी ऑपरेटर सांगेपर्यंत काहीही खाऊ-पिऊ नका किंवा औषध घेऊ नका, आणि कोणालातरी जवळ ठेवा.",
    },
    "emergency_eye": {
        "en": "",
        "hinglish": "Aankh ke liye: aankh ko ragdein ya dabayein nahi, doctor ke bina koi drops ya marham na daalein. Agar aankh mein koi chemical gaya ho to saaf bahte paani se lagatar dhote rahein. Sabse paas ke us hospital jayein jahan eye emergency (casualty) ho.",
        "hi": "आँख के लिए: आँख को रगड़ें या दबाएँ नहीं, डॉक्टर के बिना कोई ड्रॉप या मरहम न डालें। अगर आँख में कोई केमिकल गया हो तो साफ बहते पानी से लगातार धोते रहें। सबसे नज़दीकी ऐसे अस्पताल जाएँ जहाँ आँखों की इमरजेंसी (कैज़ुअल्टी) सेवा हो।",
        "mr": "डोळ्यासाठी: डोळा चोळू किंवा दाबू नका, डॉक्टरांच्या सल्ल्याशिवाय थेंब किंवा मलम घालू नका. डोळ्यात रसायन गेले असेल तर स्वच्छ वाहत्या पाण्याने सतत धुवत राहा. डोळ्यांची आणीबाणी (कॅज्युअल्टी) सेवा असलेल्या सर्वात जवळच्या रुग्णालयात जा.",
    },
    "emergency_disclaimer": {
        "en": "I'm an AI assistant and can't examine you, so please get in-person emergency care.",
        "hinglish": "Main ek AI assistant hoon aur aapko jaanch nahi sakta, isliye kripya turant in-person emergency care lein.",
        "hi": "मैं एक AI असिस्टेंट हूँ और आपकी जाँच नहीं कर सकता, इसलिए कृपया तुरंत व्यक्तिगत रूप से आपातकालीन चिकित्सा लें।",
        "mr": "मी एक AI सहाय्यक आहे आणि तुमची तपासणी करू शकत नाही, म्हणून कृपया लगेच प्रत्यक्ष आणीबाणी उपचार घ्या.",
    },
    "self_harm": {
        "en": "",
        "hinglish": "Mujhe afsos hai ki aap yeh sab jhel rahe hain, aur achha hai ki aapne bataya. Agar aap in vicharon par amal kar sakte hain ya turant khatre mein hain, to abhi 112 par call karein, aur khud ko nuksaan pahunchane wali cheezon se door kisi insaan ke paas chale jayein. Aap abhi free, 24x7 Tele-MANAS par bhi baat kar sakte hain: 14416 ya 1800-891-4416. Apne kisi bharosemand vyakti ko bata dein. Main AI hoon aur kisi insaan ki jagah nahi le sakta, par yahan baat karne ke liye hoon.",
        "hi": "मुझे दुख है कि आप यह सब झेल रहे हैं, और अच्छा है कि आपने बताया। अगर आप इन विचारों पर अमल कर सकते हैं या तुरंत खतरे में हैं, तो अभी 112 पर कॉल करें, और खुद को नुकसान पहुँचा सकने वाली चीज़ों से दूर किसी इंसान के पास चले जाएँ। आप अभी निःशुल्क, 24x7 Tele-MANAS से भी बात कर सकते हैं: 14416 या 1800-891-4416। अपने किसी भरोसेमंद व्यक्ति को बता दें। मैं AI हूँ और किसी इंसान की जगह नहीं ले सकता, पर बात करने के लिए यहाँ हूँ।",
        "mr": "तुम्ही हे सगळे सहन करत आहात याचे मला वाईट वाटते, आणि तुम्ही सांगितलेत हे चांगले झाले. या विचारांनुसार कृती करण्याची शक्यता असेल किंवा तुम्ही लगेच धोक्यात असाल तर आत्ताच 112 वर कॉल करा, आणि स्वतःला इजा होईल अशा वस्तूंपासून दूर कोणाच्यातरी जवळ जा. तुम्ही आत्ता मोफत, 24x7 Tele-MANAS शीही बोलू शकता: 14416 किंवा 1800-891-4416. तुमच्या विश्वासातील व्यक्तीला सांगा. मी AI आहे आणि माणसाची जागा घेऊ शकत नाही, पण बोलण्यासाठी इथे आहे.",
    },

    # ---------- care navigation ----------
    "screen_eye": {
        "en": "I'm sorry your eye is bothering you. One quick check first: is the pain sudden or severe, or do you have blurred vision or sudden loss of vision?",
        "hinglish": "Aapki aankh mein takleef sunkar afsos hua. Pehle ek zaroori sawal: kya dard achanak ya bahut tez hai, ya dhundhla dikh raha hai ya achanak dikhna kam/band ho gaya hai?",
        "hi": "आपकी आँख में तकलीफ़ सुनकर अफ़सोस हुआ। पहले एक ज़रूरी सवाल: क्या दर्द अचानक या बहुत तेज़ है, या धुंधला दिख रहा है, या अचानक दिखना कम/बंद हो गया है?",
        "mr": "तुमच्या डोळ्याला त्रास होत आहे हे ऐकून वाईट वाटले. आधी एक महत्त्वाचा प्रश्न: वेदना अचानक किंवा खूप तीव्र आहेत का, किंवा अंधुक दिसते आहे का, किंवा अचानक दिसणे कमी/बंद झाले आहे का?",
    },
    "screen_generic": {
        "en": "I'm sorry you're not feeling well. One quick check first: did this start suddenly, is it severe, or do you have trouble breathing, chest pain, fainting or heavy bleeding?",
        "hinglish": "Aapki tabiyat theek nahi hai, afsos hua. Pehle ek zaroori sawal: kya yeh achanak shuru hua, bahut tez hai, ya saans lene mein dikkat, seene mein dard, behoshi ya zyada khoon behna hai?",
        "hi": "आपकी तबीयत ठीक नहीं है, अफ़सोस हुआ। पहले एक ज़रूरी सवाल: क्या यह अचानक शुरू हुआ, बहुत तेज़ है, या साँस लेने में तकलीफ़, सीने में दर्द, बेहोशी या ज़्यादा खून बहना है?",
        "mr": "तुमची तब्येत बरी नाही, वाईट वाटले. आधी एक महत्त्वाचा प्रश्न: हे अचानक सुरू झाले का, खूप तीव्र आहे का, किंवा श्वास घेण्यास त्रास, छातीत दुखणे, बेशुद्ध होणे किंवा खूप रक्तस्राव आहे का?",
    },
    "screen_positive": {
        "en": "Because of what you describe, please don't wait for a routine appointment. Go to the nearest hospital emergency department now, or call 112 (108 for an ambulance in most states). Ask someone to go with you and avoid driving yourself.\n\nIf you'd like, share your PIN code or area and I'll look for hospitals near you that have an emergency service.",
        "hinglish": "Aapne jo bataya uske hisaab se routine appointment ka intezaar na karein. Abhi sabse paas ke hospital ke emergency department jayein, ya 112 par call karein (zyadatar rajyon mein ambulance ke liye 108). Kisi ko saath le jayein aur khud gaadi na chalayein.\n\nAgar chahein to apna PIN code ya area batayein, main aapke paas emergency service wale hospital dhundh dunga.",
        "hi": "आपने जो बताया उसके हिसाब से सामान्य अपॉइंटमेंट का इंतज़ार न करें। अभी सबसे नज़दीकी अस्पताल के इमरजेंसी विभाग जाएँ, या 112 पर कॉल करें (ज़्यादातर राज्यों में एम्बुलेंस के लिए 108)। किसी को साथ ले जाएँ और खुद गाड़ी न चलाएँ।\n\nचाहें तो अपना PIN कोड या इलाका बताएँ, मैं आपके पास इमरजेंसी सेवा वाले अस्पताल ढूँढ दूँगा।",
        "mr": "तुम्ही सांगितल्यावरून नेहमीच्या अपॉइंटमेंटची वाट पाहू नका. आत्ताच सर्वात जवळच्या रुग्णालयाच्या आणीबाणी विभागात जा, किंवा 112 वर कॉल करा (बहुतेक राज्यांत रुग्णवाहिकेसाठी 108). कोणालातरी सोबत घ्या आणि स्वतः गाडी चालवू नका.\n\nहवे असल्यास तुमचा PIN कोड किंवा परिसर सांगा, मी तुमच्या जवळ आणीबाणी सेवा असलेली रुग्णालये शोधतो.",
    },
    "ask_location": {
        "en": "Please share your PIN code or area (for example 400001, or Dadar, Mumbai) so I can look for nearby {what}.",
        "hinglish": "Kripya apna PIN code ya area batayein (jaise 400001 ya Dadar, Mumbai) taaki main paas ke {what} dhundh sakoon.",
        "hi": "कृपया अपना PIN कोड या इलाका बताएँ (जैसे 400001 या दादर, मुंबई) ताकि मैं पास के {what} ढूँढ सकूँ।",
        "mr": "कृपया तुमचा PIN कोड किंवा परिसर सांगा (उदा. 400001 किंवा दादर, मुंबई) म्हणजे मी जवळचे {what} शोधू शकेन.",
    },
    "ask_specialty": {
        "en": "What kind of doctor or hospital are you looking for (for example eye, dental, skin, heart, bones, children, or a general hospital)?",
        "hinglish": "Aap kis tarah ke doctor ya hospital ko dhundh rahe hain (jaise eye, dental, skin, heart, haddi, bachchon ka, ya general hospital)?",
        "hi": "आप किस तरह के डॉक्टर या अस्पताल को ढूँढ रहे हैं (जैसे आँख, दाँत, त्वचा, हृदय, हड्डी, बच्चों का, या सामान्य अस्पताल)?",
        "mr": "तुम्ही कोणत्या प्रकारचे डॉक्टर किंवा रुग्णालय शोधत आहात (उदा. डोळे, दात, त्वचा, हृदय, हाडे, मुलांचे, किंवा सामान्य रुग्णालय)?",
    },
    "ask_clarify_location": {
        "en": "I couldn't tell which area that is. Could you share your 6-digit PIN code, or the locality and city (for example Dadar, Mumbai)?",
        "hinglish": "Mujhe samajh nahi aaya ki yeh kaunsa area hai. Kya aap 6 digit ka PIN code ya locality aur city batayenge (jaise Dadar, Mumbai)?",
        "hi": "मैं समझ नहीं पाया कि यह कौन सा इलाका है। क्या आप 6 अंकों का PIN कोड या इलाका और शहर बता सकते हैं (जैसे दादर, मुंबई)?",
        "mr": "हा कोणता परिसर आहे ते मला समजले नाही. कृपया 6 अंकी PIN कोड किंवा परिसर आणि शहर सांगा (उदा. दादर, मुंबई).",
    },
    "results_intro": {
        "en": "Here {count_phrase} for {what} near {where}. These details come from {source}, so please confirm phone, timings and availability with the facility.",
        "hinglish": "{where} ke paas {what} ke liye {count_phrase}. Yeh jaankari {source} se hai, isliye phone, timing aur availability facility se confirm kar lein.",
        "hi": "{where} के पास {what} के लिए {count_phrase}। यह जानकारी {source} से है, इसलिए फ़ोन, समय और उपलब्धता अस्पताल से पुष्टि कर लें।",
        "mr": "{where} जवळ {what} साठी {count_phrase}. ही माहिती {source} मधून आहे, म्हणून फोन, वेळ आणि उपलब्धता रुग्णालयाकडून खात्री करून घ्या.",
    },
    "results_fewer": {
        "en": "I could only confirm {n} (fewer than five) in this area.",
        "hinglish": "Is area mein main sirf {n} hi confirm kar paya (paanch se kam).",
        "hi": "इस इलाके में मैं केवल {n} ही पुष्टि कर पाया (पाँच से कम)।",
        "mr": "या परिसरात मी फक्त {n} निश्चित करू शकलो (पाचपेक्षा कमी).",
    },
    "results_next": {
        "en": "To book, tell me which one you'd like, for example \"Book Hospital 2\".",
        "hinglish": "Book karne ke liye bataiye kaunsa chahiye, jaise \"Hospital 2 book karo\".",
        "hi": "बुक करने के लिए बताइए कौन सा चाहिए, जैसे \"अस्पताल 2 बुक करो\"।",
        "mr": "बुक करण्यासाठी कोणते हवे ते सांगा, उदा. \"रुग्णालय 2 बुक करा\".",
    },
    "no_results": {
        "en": "I searched but couldn't find {what} listed near {where}. Try a nearby area or the city name, or check with your doctor or local health helpline.",
        "hinglish": "Maine dhundha par {where} ke paas {what} listed nahi mile. Kisi paas ke area ya city ka naam try karein, ya apne doctor ya local health helpline se poochein.",
        "hi": "मैंने खोजा पर {where} के पास {what} सूचीबद्ध नहीं मिले। किसी पास के इलाके या शहर का नाम आज़माएँ, या अपने डॉक्टर या स्थानीय स्वास्थ्य हेल्पलाइन से पूछें।",
        "mr": "मी शोधले पण {where} जवळ {what} यादीत आढळले नाहीत. जवळचा परिसर किंवा शहराचे नाव वापरून पहा, किंवा तुमचे डॉक्टर किंवा स्थानिक आरोग्य हेल्पलाइन यांना विचारा.",
    },
    "search_unavailable": {
        "en": "I couldn't complete the hospital search right now, so I won't guess or show unverified results. Please try again in a few minutes. If this is urgent, call 112, or search \"{what} near {where}\" in Google Maps.",
        "hinglish": "Abhi main hospital search poora nahi kar paya, isliye main andaaza ya unverified results nahi dikhaunga. Kuch minute baad dobara try karein. Agar urgent hai to 112 par call karein, ya Google Maps mein \"{what} near {where}\" search karein.",
        "hi": "अभी मैं अस्पताल की खोज पूरी नहीं कर पाया, इसलिए मैं अंदाज़ा या असत्यापित नतीजे नहीं दिखाऊँगा। कुछ मिनट बाद फिर कोशिश करें। अगर ज़रूरी है तो 112 पर कॉल करें, या Google Maps में \"{what} near {where}\" खोजें।",
        "mr": "आत्ता मी रुग्णालय शोध पूर्ण करू शकलो नाही, म्हणून मी अंदाज किंवा असत्यापित निकाल दाखवणार नाही. काही मिनिटांनी पुन्हा प्रयत्न करा. तातडीचे असल्यास 112 वर कॉल करा, किंवा Google Maps मध्ये \"{what} near {where}\" शोधा.",
    },
    "search_not_configured": {
        "en": "Live hospital search isn't set up on this server yet (a Google Places API key is missing), so I can't give you verified results. If this is urgent, call 112, or search \"{what} near {where}\" in Google Maps.",
        "hinglish": "Is server par live hospital search abhi set up nahi hai (Google Places API key nahi hai), isliye main verified results nahi de sakta. Agar urgent hai to 112 par call karein, ya Google Maps mein \"{what} near {where}\" search karein.",
        "hi": "इस सर्वर पर लाइव अस्पताल खोज अभी सेट नहीं है (Google Places API key नहीं है), इसलिए मैं सत्यापित नतीजे नहीं दे सकता। अगर ज़रूरी है तो 112 पर कॉल करें, या Google Maps में \"{what} near {where}\" खोजें।",
        "mr": "या सर्व्हरवर थेट रुग्णालय शोध अजून सेट केलेला नाही (Google Places API key नाही), म्हणून मी सत्यापित निकाल देऊ शकत नाही. तातडीचे असल्यास 112 वर कॉल करा, किंवा Google Maps मध्ये \"{what} near {where}\" शोधा.",
    },
    "book_need_results": {
        "en": "I don't have a list of hospitals from you yet. Tell me what kind of doctor you need and your PIN code or area, and I'll find options you can choose from.",
        "hinglish": "Abhi mere paas aapke liye hospitals ki list nahi hai. Bataiye kis tarah ka doctor chahiye aur apna PIN code ya area, main options dhundh dunga.",
        "hi": "अभी मेरे पास आपके लिए अस्पतालों की सूची नहीं है। बताइए किस तरह का डॉक्टर चाहिए और अपना PIN कोड या इलाका, मैं विकल्प ढूँढ दूँगा।",
        "mr": "सध्या माझ्याकडे तुमच्यासाठी रुग्णालयांची यादी नाही. कोणत्या प्रकारचा डॉक्टर हवा आणि तुमचा PIN कोड किंवा परिसर सांगा, मी पर्याय शोधतो.",
    },
    "book_which": {
        "en": "Of course. Which hospital or clinic would you like? You can reply with its number from the list (for example \"2\").",
        "hinglish": "Zaroor. Aapko kaunsa hospital ya clinic chahiye? List ka number bata dijiye (jaise \"2\").",
        "hi": "ज़रूर। आपको कौन सा अस्पताल या क्लिनिक चाहिए? सूची का नंबर बता दीजिए (जैसे \"2\")।",
        "mr": "नक्कीच. तुम्हाला कोणते रुग्णालय किंवा क्लिनिक हवे? यादीतील क्रमांक सांगा (उदा. \"2\").",
    },
    "book_bad_index": {
        "en": "I only listed {n} option(s). Please choose a number between 1 and {n}.",
        "hinglish": "Maine sirf {n} option dikhaye the. Kripya 1 se {n} ke beech ka number chunein.",
        "hi": "मैंने केवल {n} विकल्प दिखाए थे। कृपया 1 से {n} के बीच का नंबर चुनें।",
        "mr": "मी फक्त {n} पर्याय दाखवले होते. कृपया 1 ते {n} मधील क्रमांक निवडा.",
    },
    "book_found_own": {
        "en": "Certainly. Here is the appointment page I found on {name}'s own website:\n{url}\n\nThis opens the hospital's own website. I have only taken you to the page; I have not booked anything.",
        "hinglish": "Zaroor. {name} ki apni website par mujhe yeh appointment page mila:\n{url}\n\nYeh hospital ki apni website kholta hai. Maine sirf aapko page tak pahunchaya hai; kuch book nahi kiya hai.",
        "hi": "ज़रूर। {name} की अपनी वेबसाइट पर मुझे यह अपॉइंटमेंट पेज मिला:\n{url}\n\nयह अस्पताल की अपनी वेबसाइट खोलता है। मैंने सिर्फ़ आपको पेज तक पहुँचाया है; कुछ बुक नहीं किया है।",
        "mr": "नक्कीच. {name} च्या स्वतःच्या वेबसाइटवर मला हे अपॉइंटमेंट पेज मिळाले:\n{url}\n\nहे रुग्णालयाची स्वतःची वेबसाइट उघडते. मी फक्त तुम्हाला पेजपर्यंत नेले आहे; काहीही बुक केलेले नाही.",
    },
    "book_found_external": {
        "en": "Certainly. {name}'s website links to this booking page, which is run by an outside provider ({host}), not by the hospital itself:\n{url}\n\nI have only taken you to the page; I have not booked anything.",
        "hinglish": "Zaroor. {name} ki website is booking page ka link deti hai, jo ek bahari provider ({host}) chalata hai, hospital khud nahi:\n{url}\n\nMaine sirf aapko page tak pahunchaya hai; kuch book nahi kiya hai.",
        "hi": "ज़रूर। {name} की वेबसाइट इस बुकिंग पेज का लिंक देती है, जिसे एक बाहरी प्रोवाइडर ({host}) चलाता है, अस्पताल खुद नहीं:\n{url}\n\nमैंने सिर्फ़ आपको पेज तक पहुँचाया है; कुछ बुक नहीं किया है।",
        "mr": "नक्कीच. {name} ची वेबसाइट या बुकिंग पेजची लिंक देते, जे बाहेरील प्रदाता ({host}) चालवतो, रुग्णालय स्वतः नाही:\n{url}\n\nमी फक्त तुम्हाला पेजपर्यंत नेले आहे; काहीही बुक केलेले नाही.",
    },
    "book_steps": {
        "en": "Usual steps on such pages (the hospital's page may differ):\n1. Open the page.\n2. Choose the department or specialty.\n3. Pick a doctor, date and time.\n4. Enter the details they ask for.\n5. Confirm on their website and keep the confirmation they send you.",
        "hinglish": "Aise pages par aam taur par steps (hospital ka page alag ho sakta hai):\n1. Page kholein.\n2. Department ya specialty chunein.\n3. Doctor, date aur time chunein.\n4. Maangi gayi jaankari bharein.\n5. Unki website par confirm karein aur jo confirmation aaye use sambhal kar rakhein.",
        "hi": "ऐसे पेजों पर आम तौर पर स्टेप्स (अस्पताल का पेज अलग हो सकता है):\n1. पेज खोलें।\n2. विभाग या स्पेशलिटी चुनें।\n3. डॉक्टर, तारीख और समय चुनें।\n4. माँगी गई जानकारी भरें।\n5. उनकी वेबसाइट पर कन्फ़र्म करें और जो कन्फ़र्मेशन आए उसे संभालकर रखें।",
        "mr": "अशा पेजवर सहसा पायऱ्या (रुग्णालयाचे पेज वेगळे असू शकते):\n1. पेज उघडा.\n2. विभाग किंवा स्पेशालिटी निवडा.\n3. डॉक्टर, तारीख आणि वेळ निवडा.\n4. मागितलेली माहिती भरा.\n5. त्यांच्या वेबसाइटवर निश्चित करा आणि येणारी पुष्टी जपून ठेवा.",
    },
    "book_not_found": {
        "en": "I couldn't verify an online booking page for {name}. {fallback}\n\nI have not booked anything.",
        "hinglish": "{name} ka online booking page main verify nahi kar paya. {fallback}\n\nMaine kuch book nahi kiya hai.",
        "hi": "मैं {name} का ऑनलाइन बुकिंग पेज सत्यापित नहीं कर पाया। {fallback}\n\nमैंने कुछ बुक नहीं किया है।",
        "mr": "मी {name} चे ऑनलाइन बुकिंग पेज सत्यापित करू शकलो नाही. {fallback}\n\nमी काहीही बुक केलेले नाही.",
    },
    "book_fallback_phone": {
        "en": "You can call them on {phone} and ask for OPD or appointment booking.",
        "hinglish": "Aap unhe {phone} par call karke OPD ya appointment booking ke liye poochh sakte hain.",
        "hi": "आप उन्हें {phone} पर कॉल करके OPD या अपॉइंटमेंट बुकिंग के लिए पूछ सकते हैं।",
        "mr": "तुम्ही त्यांना {phone} वर कॉल करून OPD किंवा अपॉइंटमेंट बुकिंगबद्दल विचारू शकता.",
    },
    "book_fallback_site": {
        "en": "Their website is {url}; look for an appointment or contact section there.",
        "hinglish": "Unki website {url} hai; wahan appointment ya contact section dekhein.",
        "hi": "उनकी वेबसाइट {url} है; वहाँ अपॉइंटमेंट या संपर्क सेक्शन देखें।",
        "mr": "त्यांची वेबसाइट {url} आहे; तिथे अपॉइंटमेंट किंवा संपर्क विभाग पहा.",
    },
    "book_fallback_none": {
        "en": "I don't have a verified phone number or website for it, so please look it up on Google Maps or ask at the hospital.",
        "hinglish": "Mere paas iska verified phone number ya website nahi hai, isliye Google Maps par dekhein ya hospital se poochein.",
        "hi": "मेरे पास इसका सत्यापित फ़ोन नंबर या वेबसाइट नहीं है, इसलिए Google Maps पर देखें या अस्पताल से पूछें।",
        "mr": "माझ्याकडे याचा सत्यापित फोन नंबर किंवा वेबसाइट नाही, म्हणून Google Maps वर पहा किंवा रुग्णालयात विचारा.",
    },
    "booked_claim": {
        "en": "Glad you've taken that step. I can't see or confirm bookings made on a hospital's website, so I can't tell you whether it has gone through. Please check for the confirmation message or reference number from the hospital. If you don't receive one, call them to confirm. Would you like me to set a reminder for the appointment?",
        "hinglish": "Achha laga ki aapne yeh kadam uthaya. Hospital ki website par hui booking main dekh ya confirm nahi kar sakta, isliye main nahi keh sakta ki woh confirm hai. Kripya hospital se aaya confirmation message ya reference number dekhein. Agar na mile to unhe call karke confirm karein. Kya main appointment ke liye reminder laga doon?",
        "hi": "अच्छा लगा कि आपने यह कदम उठाया। अस्पताल की वेबसाइट पर हुई बुकिंग मैं देख या कन्फ़र्म नहीं कर सकता, इसलिए मैं नहीं कह सकता कि वह कन्फ़र्म है। कृपया अस्पताल से आया कन्फ़र्मेशन संदेश या रेफ़रेंस नंबर देखें। न मिले तो उन्हें कॉल करके पुष्टि करें। क्या मैं अपॉइंटमेंट के लिए रिमाइंडर लगा दूँ?",
        "mr": "तुम्ही हे पाऊल उचलले हे छान. रुग्णालयाच्या वेबसाइटवर झालेले बुकिंग मी पाहू किंवा निश्चित करू शकत नाही, म्हणून ते निश्चित आहे असे मी सांगू शकत नाही. कृपया रुग्णालयाकडून आलेला पुष्टी संदेश किंवा संदर्भ क्रमांक पहा. तो न मिळाल्यास त्यांना कॉल करून खात्री करा. मी अपॉइंटमेंटसाठी रिमाइंडर लावू का?",
    },
    "screen_reask": {
        "en": "Sorry, I didn't catch that. Is it sudden or severe, or have you lost vision, had breathing trouble, chest pain, fainting or heavy bleeding? Please answer yes or no.",
        "hinglish": "Maaf kijiye, samajh nahi aaya. Kya yeh achanak ya bahut tez hai, ya dikhna band hua, saans mein dikkat, seene mein dard, behoshi ya zyada khoon behna hai? Kripya haan ya na mein batayein.",
        "hi": "माफ़ कीजिए, समझ नहीं आया। क्या यह अचानक या बहुत तेज़ है, या दिखना बंद हुआ, साँस में तकलीफ़, सीने में दर्द, बेहोशी या ज़्यादा खून बहना है? कृपया हाँ या नहीं में बताइए।",
        "mr": "माफ करा, समजले नाही. हे अचानक किंवा खूप तीव्र आहे का, किंवा दिसणे बंद झाले, श्वासाचा त्रास, छातीत दुखणे, बेशुद्धी किंवा खूप रक्तस्राव आहे का? कृपया होय किंवा नाही असे सांगा.",
    },
    "lbl_address": {"en": "Address", "hinglish": "Address", "hi": "पता", "mr": "पत्ता"},
    "lbl_phone": {"en": "Phone", "hinglish": "Phone", "hi": "फ़ोन", "mr": "फोन"},
    "lbl_website": {"en": "Official website", "hinglish": "Official website", "hi": "आधिकारिक वेबसाइट", "mr": "अधिकृत वेबसाइट"},
    "lbl_specialty": {"en": "Specialty", "hinglish": "Specialty", "hi": "विशेषता", "mr": "विशेषता"},
    "lbl_booking": {"en": "Book appointment", "hinglish": "Appointment book karein", "hi": "अपॉइंटमेंट बुक करें", "mr": "अपॉइंटमेंट बुक करा"},
    "lbl_booking_unverified": {
        "en": "online booking link not verified",
        "hinglish": "online booking link verify nahi hua",
        "hi": "ऑनलाइन बुकिंग लिंक सत्यापित नहीं हुआ",
        "mr": "ऑनलाइन बुकिंग लिंक सत्यापित झाली नाही",
    },
    "lbl_not_listed": {"en": "not listed", "hinglish": "listed nahi", "hi": "सूचीबद्ध नहीं", "mr": "यादीत नाही"},
}

_WHAT_LOCAL = {
    "hi": {"eye": "आँखों के क्लिनिक और अस्पताल", "dental": "दाँतों के क्लिनिक", "skin": "त्वचा विशेषज्ञ", "ent": "ENT विशेषज्ञ", "heart": "हृदय अस्पताल", "ortho": "हड्डी और जोड़ों के अस्पताल", "child": "बच्चों के अस्पताल", "women": "महिला स्वास्थ्य और प्रसूति अस्पताल", "general": "अस्पताल"},
    "mr": {"eye": "डोळ्यांचे क्लिनिक आणि रुग्णालये", "dental": "दंत क्लिनिक", "skin": "त्वचा तज्ज्ञ", "ent": "ENT तज्ज्ञ", "heart": "हृदय रुग्णालये", "ortho": "हाडे आणि सांधे रुग्णालये", "child": "मुलांची रुग्णालये", "women": "महिला आरोग्य आणि प्रसूती रुग्णालये", "general": "रुग्णालये"},
    "hinglish": {"eye": "eye clinic aur hospital", "dental": "dental clinic", "skin": "skin specialist", "ent": "ENT specialist", "heart": "heart hospital", "ortho": "haddi aur jodon ke hospital", "child": "bachchon ke hospital", "women": "mahila swasthya aur maternity hospital", "general": "hospital"},
}

_WHAT_LABELS = {
    "eye": "eye clinics and hospitals",
    "dental": "dental clinics",
    "skin": "skin specialists",
    "ent": "ENT specialists",
    "heart": "heart hospitals",
    "ortho": "bone and joint hospitals",
    "child": "children's hospitals",
    "women": "women's health and maternity hospitals",
    "general": "hospitals",
}


def what_label(specialty_key: Optional[str], lang: Optional[str] = "en") -> str:
    key = specialty_key or "general"
    local = _WHAT_LOCAL.get(lang or "en")
    if local and key in local:
        return local[key]
    return _WHAT_LABELS.get(key, "hospitals")


def tr(key: str, lang: Optional[str] = "en", **fmt) -> str:
    """Message `key` in `lang` (falls back to English), with {placeholders} filled."""
    entry = M[key]
    text = entry.get(lang or "en") or entry["en"]
    return text.format(**fmt) if fmt else text
