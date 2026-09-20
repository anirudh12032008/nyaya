"""Hindi for the interface chrome, keyed by the English string.

Only UI text lives here. Case content - drafts, summaries, verifier notes - comes
back from the model in whatever language the client wrote in, so it is left alone.
A missing key means the English shows through, which is the safe failure.
"""

HI = {
    # ── sidebar ─────────────────────────────────────────────────────────────
    "Home": "होम",
    "New intake": "नया मामला",
    "Cases": "केस",
    "Document analyzer": "दस्तावेज़ जाँच",
    "Admin": "प्रशासन",
    "Guided tour": "गाइड",
    "Citizen": "नागरिक",
    "Volunteer / Lawyer": "स्वयंसेवक / वकील",
    "Help": "मदद",
    "I am a": "मैं हूँ",
    "urgent": "तत्काल",
    "Clinic": "क्लिनिक",
    "Madhya Pradesh": "मध्य प्रदेश",
    "Get help with your problem": "अपनी समस्या में मदद पाएँ",
    "Run intakes and manage cases": "मामले दर्ज करें और संभालें",
    "Clinic head: oversight and settings": "क्लिनिक प्रमुख: निगरानी और सेटिंग्स",

    # ── home ────────────────────────────────────────────────────────────────
    "Good morning, clinic desk": "सुप्रभात, क्लिनिक डेस्क",
    "Good afternoon, clinic desk": "नमस्कार, क्लिनिक डेस्क",
    "Good evening, clinic desk": "शुभ संध्या, क्लिनिक डेस्क",
    "Turn problems into possibilities - intake, triage and drafting in one place.":
        "समस्या से समाधान तक - सुनवाई, छँटाई और मसौदा, सब एक जगह।",
    "Nyaya · Madhya Pradesh legal aid": "न्याय · मध्य प्रदेश विधिक सहायता",
    "Start a matter for a citizen or volunteer.":
        "किसी नागरिक या स्वयंसेवक के लिए मामला शुरू करें।",
    "New intake →": "नया मामला →",
    "My cases": "मेरे केस",
    "For lawyers and volunteers tracking their queue.":
        "वकीलों और स्वयंसेवकों की अपनी सूची।",
    "My cases →": "मेरे केस →",
    "Analyze a document": "दस्तावेज़ जाँचें",
    "Upload a document for Nyaya to read.": "न्याय को पढ़ने के लिए दस्तावेज़ भेजें।",
    "Analyze a document →": "दस्तावेज़ जाँचें →",
    "No cases yet": "अभी कोई केस नहीं",
    "Take the first intake above and the clinic queue will fill up here.":
        "ऊपर से पहला मामला दर्ज करें, सूची यहाँ भरने लगेगी।",
    "Deadline watchlist": "समय-सीमा सूची",
    "Soonest limitation first": "सबसे नज़दीकी सीमा पहले",
    "Nothing here right now.": "अभी यहाँ कुछ नहीं है।",
    "Open": "खोलें",
    "Your case, our AI agents": "आपका मामला, हमारे AI एजेंट",
    "unassigned": "अनिर्धारित",

    # pipeline strip
    "Understand": "समझें",
    "Listen to the client's story": "क्लाइंट की बात सुनें",
    "Classify": "वर्गीकरण",
    "Module, urgency, limitation": "श्रेणी, तात्कालिकता, समय-सीमा",
    "Extract": "निकालें",
    "Read the papers they brought": "लाए गए कागज़ पढ़ें",
    "Check": "जाँचें",
    "Free legal aid under s.12": "धारा 12 के तहत मुफ़्त विधिक सहायता",
    "Prepare": "तैयार करें",
    "Notice, complaint, application": "नोटिस, शिकायत, आवेदन",
    "Review": "समीक्षा",
    "Citations and gaps flagged": "हवाले और कमियाँ चिह्नित",

    # ── deadline badges ─────────────────────────────────────────────────────
    "no limitation date": "कोई समय-सीमा नहीं",
    "%d days left": "%d दिन बचे",
    "limitation passed %dd ago": "समय-सीमा %d दिन पहले बीत गई",

    # ── new intake ──────────────────────────────────────────────────────────
    "Client's statement": "क्लाइंट का बयान",
    "Hindi, Hinglish or English - write it the way the client said it.":
        "हिंदी, हिंग्लिश या अंग्रेज़ी - जैसा क्लाइंट ने कहा वैसा ही लिखें।",
    "Start from an example": "उदाहरण से शुरू करें",
    "Rent agreement PDF (optional)": "किरायानामा PDF (वैकल्पिक)",
    "A rent agreement helps the tenant module flag unfair clauses.":
        "किरायानामा से अनुचित शर्तें पकड़ने में मदद मिलती है।",
    "Case summary": "मामले का सार",
    "Next steps": "अगले कदम",
    "One question before drafting": "मसौदे से पहले एक सवाल",
    "Continue": "आगे बढ़ें",
    "No intake analysed yet": "अभी कोई मामला जाँचा नहीं गया",
    "Write or paste the client's statement first.":
        "पहले क्लाइंट का बयान लिखें या चिपकाएँ।",

    # ── document analyzer ───────────────────────────────────────────────────
    "Upload a PDF or TXT document to start.":
        "शुरू करने के लिए PDF या TXT दस्तावेज़ भेजें।",
    "Document analysis completed.": "दस्तावेज़ की जाँच पूरी हुई।",
    "Not specified.": "उल्लेख नहीं है।",
    "No potential issues were identified.": "कोई संभावित समस्या नहीं मिली।",
    "📋 Document Type": "📋 दस्तावेज़ का प्रकार",
    "👥 Parties & 📅 Important Dates": "👥 पक्षकार और 📅 ज़रूरी तारीख़ें",
    "⚖️ Laws & Sections": "⚖️ कानून और धाराएँ",
    "📌 Key Clauses & 📝 Obligations": "📌 मुख्य शर्तें और 📝 दायित्व",
    "⏰ Deadlines": "⏰ समय-सीमाएँ",
    "⚠️ Potential Issues to Review": "⚠️ देखने योग्य संभावित समस्याएँ",
    "✅ Required Actions": "✅ ज़रूरी कार्रवाई",

    # ── document analyzer, continued ────────────────────────────────────────
    "📄 Legal Document Analyzer": "📄 कानूनी दस्तावेज़ जाँच",
    "Upload a legal document": "कानूनी दस्तावेज़ भेजें",
    "Supported formats: PDF and TXT.": "स्वीकृत प्रारूप: PDF और TXT।",
    "Uploaded:": "भेजा गया:",
    "🔍 Analyze Document": "🔍 दस्तावेज़ जाँचें",
    "Not specified": "उल्लेख नहीं है",
    "👥 Parties": "👥 पक्षकार",
    "📅 Important Dates": "📅 ज़रूरी तारीख़ें",
    "📌 Key Clauses": "📌 मुख्य शर्तें",
    "📝 Obligations": "📝 दायित्व",
    "This analysis is informational and does not constitute legal advice.":
        "यह जाँच केवल जानकारी के लिए है, कानूनी सलाह नहीं।",
    """
        Upload a legal document and Nyaya will extract:

        - 👥 Parties
        - 📅 Important dates
        - \u2696\ufe0f Laws and sections
        - 📌 Key clauses
        - 📝 Obligations
        - ⏰ Deadlines
        - ⚠️ Potential issues to review
        - ✅ Required actions
        """: """
        कानूनी दस्तावेज़ भेजें, न्याय इन्हें निकालेगा:

        - 👥 पक्षकार
        - 📅 ज़रूरी तारीख़ें
        - \u2696\ufe0f कानून और धाराएँ
        - 📌 मुख्य शर्तें
        - 📝 दायित्व
        - ⏰ समय-सीमाएँ
        - ⚠️ देखने योग्य संभावित समस्याएँ
        - ✅ ज़रूरी कार्रवाई
        """,
}
