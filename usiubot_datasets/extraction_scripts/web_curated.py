"""Curated, evidence-checked records from the official website snapshots (collected 2026-11-01).

Every evidence string must occur in the named snapshot (whitespace-normalised); build_web_dataset.py
stops otherwise. Nothing here is approved: all records are drafts pending university verification.
"""
# ======================================================================================
# CURATED RECORDS (each evidence string must appear in the snapshot named by page id)
# ======================================================================================
P_CONTACT = "about-us__contact-us"
P_FEEPAY = "admission-fees__fee-payment-refunds"
P_TUITION = "tuition-fees"
P_ADMREQ = "admission-requirements"
P_HOWTO = "how-to-apply"
P_INTAKE = "intake"
P_INTL = "international-applicants"
P_FINAID = "financial-aid"
P_COMM = "2026-48th-commencement"
P_HOUSING = "student-life__housing-accommodation"
P_HEALTH = "health-wellness"
P_LIB = "academics__library-and-e-resources"
P_CAREERS = "placement-careers"
P_CBET = "admission-fees__cbet-realignment"
P_DIS = "disability-inclusion"
P_ADMFEES = "admission-fees"
P_VMV = "about-us__vision-mission-values"
P_ABOUT = "about-us"
P_ACC = "about-us__accreditations"
P_CAL = "academics__academic-calendar"
P_CATALOG = "academics__academic-catalog"
P_SCHOOLS = "academics__our-schools"

# (record id, page, office as printed, USIUBOT routing department, type, value as printed, evidence, issues)
WEB_CONTACTS = [
    ("CON-WEB-01", P_CONTACT, "Admissions Office", "admissions", "telephone", "+254 730 116 247 /300 /397 /503 /522",
     "Tel: +254 730 116 247 /300 /397 /503 /522", ["W05", "W02"]),
    ("CON-WEB-02", P_CONTACT, "Admissions Office", "admissions", "email", "admit@usiu.ac.ke", "Mail: admit@usiu.ac.ke", []),
    ("CON-WEB-03", P_CONTACT, "Admissions Office", "admissions", "whatsapp", "+254 755 844 849",
     "Whatsapp: +254 755 844 849", []),
    ("CON-WEB-04", P_CONTACT, "Library", "library", "telephone", "+257 730 116 429/254/549/294",
     "Tel: +257 730 116 429/254/549/294", ["W04"]),
    ("CON-WEB-05", P_CONTACT, "Library", "library", "whatsapp", "0782 620 858", "Whatsapp: 0782 620 858", []),
    ("CON-WEB-06", P_CONTACT, "Registrar", "registrar", "telephone", "+257 730 116 786", "Tel: +257 730 116 786", ["W04"]),
    ("CON-WEB-07", P_CONTACT, "Registrar", "registrar", "email", "registrar@usiu.ac.ke", "Mail: registrar@usiu.ac.ke", ["V26"]),
    ("CON-WEB-08", P_CONTACT, "Placement and Careers", "careers", "telephone", "0730 116 778 /779 /796",
     "Tel: 0730 116 778 /779 /796", ["V13"]),
    ("CON-WEB-09", P_CONTACT, "Placement and Careers", "careers", "email", "careeroffice@usiu.ac.ke",
     "Mail: careeroffice@usiu.ac.ke", ["W01"]),
    ("CON-WEB-10", P_CONTACT, "IT Helpdesk", "ict", "telephone", "+254 730 116 333", "Tel: +254 730 116 333", []),
    ("CON-WEB-11", P_CONTACT, "IT Helpdesk", "ict", "email", "helpdesk@usiu.ac.ke", "Mail: helpdesk@usiu.ac.ke", ["W01"]),
    ("CON-WEB-12", P_CONTACT, "IT Helpdesk", "ict", "email", "multimedia@usiu.ac.ke", "Mail: multimedia@usiu.ac.ke", ["W01"]),
    ("CON-WEB-13", P_CONTACT, "Finance", "finance", "telephone", "+254 730 116 403", "Tel: +254 730 116 403", ["W06"]),
    ("CON-WEB-14", P_CONTACT, "Finance", "finance", "email", "finance@usiu.ac.ke", "Mail: finance@usiu.ac.ke", ["W01"]),
    ("CON-WEB-15", P_CONTACT, "Alumni Relations", "alumni", "telephone", "+254 730 116 417 / +254 730 116 895",
     "Tel: +254 730 116 417 / +254 730 116 895", []),
    ("CON-WEB-16", P_CONTACT, "Alumni Relations", "alumni", "email", "alumni@usiu.ac.ke", "Mail: alumni@usiu.ac.ke", []),
    ("CON-WEB-17", P_CONTACT, "Main Lines", "general_university", "telephone", "+254 730 116 000 /290 /291",
     "Main Lines: +254 730 116 000 /290 /291", ["W05"]),
    ("CON-WEB-18", P_CONTACT, "United States International University – Africa", "general_university", "postal_address",
     "USIU Road, Off Thika Road (Exit 7), P. O. Box 14634 – 00800, Nairobi, Kenya, East Africa.",
     "USIU Road, Off Thika Road (Exit 7), P. O. Box 14634 – 00800, Nairobi, Kenya, East Africa.", []),
    ("CON-WEB-19", P_FEEPAY, "Contact Finance", "finance", "telephone", "+254 730 116 175/217/189",
     "+254 730 116 175/217/189", ["W06"]),
    ("CON-WEB-20", P_FEEPAY, "Contact Finance", "finance", "email", "finance@usiu.ac.ke",
     "please reach out to finance via phone call or email", []),
    ("CON-WEB-21", P_FEEPAY, "Credit Control Office (instalment plans)", "finance", "telephone", "+254 730 116 538",
     "Credit Control Office on: +254 730 116 538", ["W06"]),
    ("CON-WEB-22", P_FEEPAY, "Credit Control Office (instalment plans)", "finance", "email", "credit@usiu.ac.ke",
     "or send an email to: credit@usiu.ac.ke", []),
    ("CON-WEB-23", P_FEEPAY, "Finance Department (Student Accounts; refund status)", "finance", "telephone",
     "0730116509/221/538/224", "Finance Department (Student Accounts – 0730116509/221/538/224)", ["W06"]),
    ("CON-WEB-24", P_FEEPAY, "Library & Information Center: Chief Librarian (clearance)", "library", "telephone",
     "0730116294", "Library & Information Center: Chief Librarian (0730116294)", []),
    ("CON-WEB-25", P_FEEPAY, "Department of Housing: Housing Manager (clearance)", "student_affairs", "telephone",
     "0730116265", "Department of Housing: Housing Manager (0730116265)", []),
    ("CON-WEB-26", P_FEEPAY, "Student Life: Senior Student Life Officer (clearance)", "student_affairs", "telephone",
     "0730116792/747", "Senior Student Life Officer – 0730116792/747", []),
    ("CON-WEB-27", P_FEEPAY, "Student Life: Dean of Students (clearance: disciplinary, student leaders)",
     "student_affairs", "telephone", "0730116781/787", "Disciplinary (Dean of Students – 0730116781/787)", []),
    ("CON-WEB-28", P_FEEPAY, "Graduation Gown return (clearance)", "registrar", "telephone", "0730116786/785/870",
     "Graduation Gown return 0730116786/785/870", []),
    ("CON-WEB-29", P_FEEPAY, "Degree completion (clearance)", "registrar", "telephone", "0730116785/870/786",
     "Degree completion 0730116785/870/786", []),
    ("CON-WEB-30", P_FEEPAY, "Health Services: Principal Medical Officer (clearance)", "student_affairs", "telephone",
     "0730116759", "Principal Medical Officer (0730116759)", []),
    ("CON-WEB-31", P_FEEPAY, "Office of the Registrar: Exit Form (clearance)", "registrar", "telephone", "0730116783",
     "Exit Form (Registrar – 0730116783)", []),
    ("CON-WEB-32", P_FEEPAY, "Office of Alumni Relations: Alumni Relations Officer (clearance)", "alumni", "telephone",
     "0730116617/585", "Alumni Relations Officer (0730116617/585)", []),
    ("CON-WEB-33", P_FEEPAY, "Department of Hospitality: Cafeteria Manager (clearance)", "student_affairs", "telephone",
     "0730116623", "Cafeteria Manager (0730116623)", []),
    ("CON-WEB-34", P_ADMREQ, "Contact Admissions", "admissions", "telephone",
     "+254 730 116 290 / 291 / 247 / 300 / 397 / 503 / 522", "+254 730 116 290 / 291 / 247 / 300 / 397 / 503 / 522", ["W05"]),
    ("CON-WEB-35", P_INTAKE, "Admissions Main Line", "admissions", "telephone", "+254 730 116 290 /291",
     "Admissions Main Line +254 730 116 290 /291", ["W05", "W02"]),
    ("CON-WEB-36", P_FINAID, "Financial Aid (EAC Scholarship enquiries)", "financial_aid", "email", "finaid@usiu.ac.ke",
     "finaid@usiu.ac.ke", []),
    ("CON-WEB-37", P_FINAID, "Financial Aid (2026 scholarship call only)", "financial_aid", "email", "finaid26@usiu.ac.ke",
     "Email your completed application form and supporting documents to: finaid26@usiu.ac.ke", ["W10"]),
    ("CON-WEB-38", P_FINAID, "USIU-Africa Financial Aid Office", "financial_aid", "location", "Freida Brown Building",
     "USIU-Africa Financial Aid Office, located at the Freida Brown Building", []),
    ("CON-WEB-39", P_COMM, "Graduation queries", "registrar", "email", "graduation@usiu.ac.ke",
     "For all graduation queries, kindly contact: graduation@usiu.ac.ke", []),
    ("CON-WEB-40", P_COMM, "Yearbook queries", "marketing", "email", "yearbook@usiu.ac.ke",
     "For Yearbook queries kindly contact yearbook@usiu.ac.ke", []),
    ("CON-WEB-41", P_COMM, "University Security", "security", "telephone", "0730 116 266 / 0730 116 461",
     "University Security: 0730 116 266 / 0730 116 461", ["V14"]),
    ("CON-WEB-42", P_HOUSING, "Housing Officer", "student_affairs", "email", "housing@usiu.ac.ke",
     "Email: housing@usiu.ac.ke", []),
    ("CON-WEB-43", P_HOUSING, "Housing Officer", "student_affairs", "telephone", "+254 730 116 265",
     "Office Number: +254 730 116 265", []),
    ("CON-WEB-44", P_HOUSING, "Campus emergency (residents)", "security", "extension", "Ext. 262, 202, 327, 279, 266",
     "Ext. 262, 202, 327, 279, 266 – all available 24 hours a day", ["V14"]),
    ("CON-WEB-45", P_HEALTH, "Counseling Services", "student_affairs", "telephone", "+254-730 116 748/746/750/791/797/817",
     "Phone: +254-730 116 748/746/750/791/797/817", ["V13"]),
    ("CON-WEB-46", P_HEALTH, "Counseling Services", "student_affairs", "email", "counsel@usiu.ac.ke",
     "E-mail: counsel@usiu.ac.ke", []),
    ("CON-WEB-47", P_HEALTH, "Health Center (emergency)", "student_affairs", "telephone", "+254 730 116 760 /761 /762 /271",
     "+254 730 116 760 /761 /762 /271", ["V12", "W02"]),
    ("CON-WEB-48", P_HEALTH, "Health Center (emergency)", "student_affairs", "telephone", "+254 798 294 538",
     "+254 798 294 538", ["V12", "W02"]),
    ("CON-WEB-49", P_LIB, "Director, Library and Information Center", "library", "email", "library@usiu.ac.ke",
     "Mail: library@usiu.ac.ke", []),
    ("CON-WEB-50", P_LIB, "Director, Library and Information Center", "library", "telephone", "0730116429/430",
     "Tel: 0730116429/430", []),
    ("CON-WEB-51", P_LIB, "Ask a Librarian", "library", "email", "askalibrarian@usiu.ac.ke",
     "sending an email to askalibrarian@usiu.ac.ke", []),
    ("CON-WEB-52", P_CAREERS, "Placement and Careers", "careers", "email", "careeroffice@usiu.ac.ke",
     "Email: careeroffice@usiu.ac.ke", []),
    ("CON-WEB-53", P_CBET, "Director, Quality Assurance Services (CBET)", "academic_programmes", "email", "cbet@usiu.ac.ke",
     "Director, Quality Assurance Services | cbet@usiu.ac.ke", []),
    ("CON-WEB-54", P_DIS, "Disability Inclusion (Freida Brown Student Center, Ground Floor)", "student_affairs",
     "telephone", "+254 730 116 830", "+254 730 116 830", ["W02"]),
]

# Bank accounts on the Fee Payment & Refunds page: (id, bank as printed, account name, currency, number,
# bank code, branch code, branch, swift, intermediary)
WEB_BANKS = [
    ("BANK-WEB-01", "NCBA BANK KENYA LTD", "USIU or U.S International University", "KES", "6438840014", "07", "000",
     "Upper Hill", "CBAFKENX", ""),
    ("BANK-WEB-02", "NCBA BANK KENYA LTD", "USIU or U.S International University", "USD", "6462210014", "07", "000",
     "Upper Hill", "CBAFKENX", "JP Morgan Chase Bank, New York (CHASUS33)"),
    ("BANK-WEB-03", "COOPERATIVE BANK OF KENYA", "United States International University – Africa", "KES",
     "01120002134100", "11", "142", "CO-OP House, Haile Selassie Avenue", "KCOOKENA", ""),
    ("BANK-WEB-04", "STANDARD CHARTERED BANK KENYA", "United States International University – Africa", "KES",
     "0104023439700", "02", "084", "Kenyatta Avenue", "SCBLKENX", ""),
    ("BANK-WEB-05", "KENYA COMMERCIAL BANK", "United States International University – Africa", "KES", "1179516710",
     "01", "308", "Thika Road Mall", "KCBLKENX", ""),
    ("BANK-WEB-06", "ABSA BANK KENYA PLC", "United States International University", "KES", "2037727558", "03", "106",
     "Sarit", "BARCKENX", ""),
    ("BANK-WEB-07", "ABSA BANK KENYA PLC", "United States International University", "USD", "2047249840", "03", "106",
     "Sarit", "BARCKENX", "Citi Bank, New York (CITIUS33)"),
    ("BANK-WEB-08", "STANBIC BANK KENYA", "United States International University", "KES", "0100011682469", "31", "021",
     "Garden City Branch", "SBICKENX", ""),
    ("BANK-WEB-09", "STANBIC BANK KENYA", "United States International University", "USD", "0100011682523", "31", "021",
     "Garden City Branch", "SBICKENX", "JP Morgan Chase Bank, New York (CHASUS33)"),
    ("MPESA-WEB-01", "Lipa na M-PESA", "Account number: Student ID – (hyphen) then purpose code",
     "KES", "Business number 516900", "", "", "", "", ""),
]

# (id, page, topic, rule as printed (evidence = the rule itself unless given), issues)
WEB_FEE_RULES = [
    ("FEE-WEB-01", P_FEEPAY, "Fee deadline", "Fees must be paid in FULL on or before the date the semester begins.", []),
    ("FEE-WEB-02", P_FEEPAY, "Freshmen", "All freshmen must pay fees in full to be able to register for courses.", []),
    ("FEE-WEB-03", P_FEEPAY, "Interest on balances",
     "NB: There is an interest charge of 1.5% per month on any outstanding debit balance from the 2nd day of the semester.",
     ["V28"]),
    ("FEE-WEB-04", P_FEEPAY, "Returned cheques",
     "A penalty of 10% of the check amount to a maximum of KES.5,000 is charged on any returned checks", []),
    ("FEE-WEB-05", P_FEEPAY, "Cash limit at cash office",
     "Cash payments in excess of KES 1, 000 are not accepted at the cash office.", ["W09"]),
    ("FEE-WEB-06", P_TUITION, "No cash at Finance Office", "No cash payments are accepted in the Finance Office.", ["W09"]),
    ("FEE-WEB-07", P_FEEPAY, "Instalment plan (3Pay)",
     "Indicate your Installment Payment Plan Proposal (Maximum, 3 Installments Only per Semester)", []),
    ("FEE-WEB-08", P_FEEPAY, "Instalment plan eligibility",
     "You are Registered for the current Semester and have No Tuition Fee balances from the previous Semester", []),
    ("FEE-WEB-09", P_FEEPAY, "Instalment plan first payment",
     "You have Deposited to our Bank or M-pesa Account, your 1st Payment Installment Amount before Submitting your Application", []),
    ("FEE-WEB-10", P_FEEPAY, "Instalment plan documents",
     "Attach copies of the Mandatory Documents required (Data Sheet, KRA Pin Certificate,", []),
    ("FEE-WEB-11", P_FEEPAY, "Tuition refunds (continuing students)",
     "Tuition cannot be refunded for continuing students’ .However, upon final clearance from the university, remaining "
     "tuition will be refunded to the sponsor /student’s declared bank account.", ["V04"]),
    ("FEE-WEB-12", P_FEEPAY, "Refund processing time",
     "Refund forms are collected up to the 24th of every month and refunds processed by the 2nd week of the following "
     "month. Refunds will take a maximum of 3 weeks from the date of submission;", []),
    ("FEE-WEB-13", P_FEEPAY, "Refund method", "All refunds are paid via Electronic Funds Transfer;", []),
    ("FEE-WEB-14", P_FEEPAY, "Who is refunded",
     "Only graduating or exiting students shall be refunded. No continuing students shall be refunded;", []),
    ("FEE-WEB-15", P_FEEPAY, "Refund steps", "Apply for final clearance online:", []),
    ("FEE-WEB-16", P_FEEPAY, "Upkeep money", "Upkeep money should not be deposited in USIU-Africa Bank account.", []),
    ("FEE-WEB-17", P_FEEPAY, "Transfers between students", "Students are not allowed to transfer funds to other students.", []),
    ("FEE-WEB-18", P_FEEPAY, "Bank deposit receipting",
     "All cash deposits made at the bank shall be receipted into the student accounts on the next working day.", []),
    ("FEE-WEB-19", P_FEEPAY, "M-PESA account number format", "Student ID – (hyphen) then purpose code.", []),
    ("FEE-WEB-20", P_FEEPAY, "M-PESA purpose code for fees",
     "For Tuition Fee, Graduation fee, Diploma replacement and any other fee payment use the code – TUIT", []),
    ("FEE-WEB-21", P_FEEPAY, "Online card payment",
     "Login to the ITS Student Portal via this link.", []),
    ("FEE-WEB-22", P_TUITION, "Annual review", "Fees are subject to annual review", []),
    ("FEE-WEB-23", P_TUITION, "Non-East African rate",
     "Non-East Africans will pay 30% above local rates for tuition and all mandatory fees i.e. library, medical and "
     "student activity fees", []),
    ("FEE-WEB-24", P_TUITION, "USD exchange rate",
     "USD Exchange Rates are fixed every semester for non-east Africans, while the rate varies daily for East Africans", []),
    ("FEE-WEB-25", P_TUITION, "Thesis II re-registration",
     "In the first Registration of Thesis II, the Thesis II is charged as a full 3 unit graduate course, while the 2nd "
     "and 3rd Registration of Thesis II, is charged at 50% of the tuition.", []),
    ("FEE-WEB-26", P_TUITION, "Technology / IT lab fee", "All students will be charged ksh 3,500 for Technology fee.", ["W21"]),
    ("FEE-WEB-27", P_HOWTO, "Application fee",
     "New applicants must pay a non-refundable application fee of KES 3,500 for undergraduate applicants and KES 4000 "
     "for postgraduate applicants.", []),
    ("FEE-WEB-28", P_TUITION, "Deposit slips",
     "All payments should be made by cheque issued to United States International university – Africa (USIU-Africa), "
     "or deposited into the accounts indicated, then forward the deposit slip to the Finance Office at USIU-Africa.", ["W09"]),
    ("FEE-WEB-29", P_FEEPAY, "Deposit slips (bank deposits)", "No need to bring cash deposit slips to our cash office", ["W09"]),
    ("FEE-WEB-30", P_HOUSING, "On-campus accommodation cost (FAQ)", "KES. 30,000", ["W13"]),
]

# Admission rules (category 03): (id, page, topic, rule as printed, issues)
WEB_ADMISSION_RULES = [
    ("ADM-WEB-01", P_ADMREQ, "Undergraduate (Kenyan applicants)",
     "These include Kenya Certificate of Secondary Education (KCSE) scores of C+ and above or equivalent.", []),
    ("ADM-WEB-02", P_ADMREQ, "International high-school qualifications",
     "Students who hold other international high school qualifications will be required to submit their certificates to "
     "the Commission for University Education or other recognized bodies for equation to the KCSE.", ["M09"]),
    ("ADM-WEB-03", P_ADMREQ, "Minimum requirements do not guarantee admission",
     "In all cases, meeting minimum admissions requirements does not guarantee acceptance into the undergraduate "
     "programs at USIU-Africa.", []),
    ("ADM-WEB-04", P_ADMREQ, "Conditional admission",
     "Conditionally admitted students must present the required documents within the first semester of study. Failure "
     "to do so will prohibit further registration. Conditionally admitted students are not eligible for financial aid.", []),
    ("ADM-WEB-05", P_ADMREQ, "Undergraduate appeal",
     "An undergraduate applicant who has been denied admission may appeal the decision by writing to the Admission "
     "Office requesting a review of the application.", []),
    ("ADM-WEB-06", P_ADMREQ, "Graduate appeal",
     "A graduate applicant who has been refused admission may appeal the decision, in writing, to the academic dean or "
     "designee.", []),
    ("ADM-WEB-07", P_ADMREQ, "Forged documents",
     "An application will automatically be rejected without further recourse if any altered or forged documents are "
     "submitted.", []),
    ("ADM-WEB-08", P_ADMREQ, "Placement tests",
     "Undergraduate students are required to sit for their placement tests in English, Computer Competency and "
     "Mathematics during their first semester of study.", []),
    ("ADM-WEB-09", P_ADMREQ, "Graduate admission (university-wide)",
     "Graduate admission requirements vary depending on the degree sought.", []),
    ("ADM-WEB-10", P_ADMREQ, "Graduate admission documents", "Two letters of recommendation", []),
    ("ADM-WEB-11", P_ADMREQ, "Graduate transfer credit",
     "No transfer of credits may be applied towards graduate degree requirements.", []),
    ("ADM-WEB-12", P_ADMREQ, "Re-admission",
     "Students who are not in continuous enrolment must apply for re-admission through the Admissions Office, unless "
     "they have obtained an approved Leave of Absence.", []),
    ("ADM-WEB-13", P_ADMREQ, "Pupil's Pass (non-Kenyan applicants)",
     "Non-Kenyan applicants are required to apply for a Kenyan Pupil's Pass.", []),
    ("ADM-WEB-14", P_ADMREQ, "Evidence of financial support",
     "The evidence of financial support must be current within one year of the student's start date at the University.", []),
    ("ADM-WEB-15", P_ADMREQ, "Pupil's Pass fee waiver (EAC)",
     "Although students from Tanzania, Uganda, Rwanda and Burundi are required to apply for the Kenyan Pupil's Pass, the "
     "application fee has been waived by the Kenyan government.", []),
    ("ADM-WEB-16", P_INTL, "U.S. applicants", "U.S. citizens/permanent residents must submit their SAT or ACT scores for "
                                              "evaluation.", []),
    ("ADM-WEB-17", P_HOWTO, "How to submit an application",
     "Kindy download them, fill them then scan and send them to admit@usiu.ac.ke", []),
    ("ADM-WEB-18", P_HOWTO, "Application review",
     "The admissions office will review your application to confirm you meet our requirements.", []),
    ("ADM-WEB-19", P_INTAKE, "Processing time",
     "Documents are processed within 2-4 working days. Conditional acceptance is granted first; full admission follows "
     "verification.", []),
    ("ADM-WEB-20", P_INTAKE, "Current intake (as displayed on 2026-11-01)", "January (Spring) Semester 2027 Intake Ongoing",
     []),
    ("ADM-WEB-21", P_ADMFEES, "Intake banner (outdated)", "The May 2026 intake to USIU-Africa is now open!", ["W10"]),
    ("ADM-WEB-22", P_ADMREQ, "Special status / non-degree",
     "Students who do not intend to earn a degree at USIU-Africa may apply to be Special Status Non-Degree students.", []),
    ("ADM-WEB-23", P_ADMREQ, "Change of degree program (graduate)",
     "Graduate students who wish to change degree programs must re-apply to the new area of study and pay the "
     "applicable application fee.", []),
]

# English proficiency (category 07): (id, page, test, minimum as printed, evidence, issues)
WEB_ENGLISH = [
    ("ELIG-WEB-01", P_ADMREQ, "TOEFL (Internet Based)", "79 or higher; current within the last two years",
     "Undergraduate applicants must have a score of 79 or higher in the Internet Based) on the Test of English as a "
     "Foreign Language (TOEFL). TOEFL scores must be current within the last two years.", ["V16"]),
    ("ELIG-WEB-02", P_ADMREQ, "Cambridge Test of English Proficiency", "C or better",
     "English Proficiency may also be determined through the Cambridge Test of English Proficiency. A grade of C or "
     "better is required.", ["V16"]),
    ("ELIG-WEB-03", P_ADMREQ, "IELTS", "6 (competent user)",
     "A minimum score of 6 (competent user) is required.", ["V16"]),
    ("ELIG-WEB-04", P_ADMREQ, "USIU-Africa English Proficiency test", "C or better",
     "applicants may also pass the USIU Africa's English Proficiency test with a grade of C or better.", ["V16"]),
    ("ELIG-WEB-05", P_ADMREQ, "Exemption", "Students from countries where English is the official language are exempt",
     "Students from countries where English is the official language will be exempt from the USIU- Africa English "
     "proficiency requirement", []),
    ("ELIG-WEB-06", "programs__bachelor-of-science-in-information-systems-technology", "TOEFL (paper / computer based)",
     "550 or higher (213 computer based)",
     "Undergraduate applicants must have a score of 550 or higher (213 computer based) on the Test of English as a "
     "Foreign Language (TOEFL).", ["V16"]),
]

# Transfer credit / transcripts (category 07): (id, page, topic, rule as printed, issues)
WEB_TRANSFER = [
    ("TRF-WEB-01", P_ADMREQ, "Maximum transfer credit",
     "A maximum of 49% of credit earned may be accepted for transfer from accredited undergraduate institutions.", ["W11"]),
    ("TRF-WEB-02", P_INTL, "Maximum transfer credit",
     "A maximum of 90 trimester units of credit earned may be accepted for transfer from accredited undergraduate "
     "institutions.", ["W11"]),
    ("TRF-WEB-03", P_ADMREQ, "Residency requirement",
     "The 51% of all units toward a degree must be completed at USIU-Africa to comply with residency requirements.", ["W11"]),
    ("TRF-WEB-04", P_INTL, "Residency requirement",
     "The final 30 semester units toward a degree must be completed at USIU-Africa to comply with residency "
     "requirements.", ["W11"]),
    ("TRF-WEB-05", P_ADMREQ, "Extension credit limit",
     "No more than 24 semester units of extension credits may be applied toward the undergraduate degree requirements", ["W11"]),
    ("TRF-WEB-06", P_INTL, "Extension credit limit",
     "No more than 23 trimester units of extension credits may be applied toward the undergraduate degree requirements", ["W11"]),
    ("TRF-WEB-07", P_ADMREQ, "Minimum grade",
     "Transfer credit is accepted from accredited institutions only if the grade received is C or better.", []),
    ("TRF-WEB-08", P_ADMREQ, "Examination credit",
     "A maximum of 30 units of examination credit from all sources will be accepted by the University.", []),
    ("TRF-WEB-09", P_ADMREQ, "Pharmacy transfer",
     "NB: For the Bachelor of Pharmacy Program, the National Policy on transfer of credit, as developed by the Pharmacy & "
     "Poisons Board, shall apply.", []),
    ("TRF-WEB-10", P_ADMREQ, "Transcripts required",
     "All undergraduate applicants to USIU-Africa must submit their high school results (official transcripts or "
     "official test results).", []),
    ("TRF-WEB-11", P_ADMREQ, "Grade reports not accepted", "Student grade reports are not accepted in lieu of a transcript.", []),
    ("TRF-WEB-12", P_ADMREQ, "Translations",
     "Transcripts (records of studies) issued in languages other than English must be accompanied by a certified English "
     "translation together with a copy of the record(s) from which the translation was made.", []),
    ("TRF-WEB-13", P_ADMREQ, "Documents not returned",
     "Documents submitted to the University in support of a student's application become the property of the "
     "University, and the documents cannot be returned or forwarded.", []),
    ("TRF-WEB-14", P_INTL, "International Baccalaureate",
     "the University will grant advanced placement of six trimester units for each higher level result of four, five, "
     "six, or seven up to a maximum of 30 units.", []),
    ("TRF-WEB-15", P_INTL, "SAT/ACT exemption (ambiguous)",
     "Students who have completed 18 semester units or 27 semester units will not be required to submit SAT or ACT scores.",
     ["W11"]),
    ("TRF-WEB-16", P_ADMREQ, "Transfer evaluation copy",
     "Students can request a copy of the transfer evaluation from the Registrar's Office.", []),
]

# Financial aid on the website (category 04): (id, page, programme as printed, type, coverage/eligibility evidence, issues)
WEB_FINAID = [
    ("AID-WEB-01", P_FINAID, "Full USIU-Africa Scholarship", "Institutional scholarship",
     "covers the full costs of tuition, books, technology, laboratory, room and board fees in the university hostels. "
     "Applicants must have attained a mean grade of B+ (Plus) or better, with at least a B plain in English and "
     "Mathematics.", []),
    ("AID-WEB-02", P_FINAID, "Partial USIU-Africa Scholarship", "Institutional scholarship",
     "This is merit and need based 100% tuition-only scholarship for applicants with demonstrated financial need.", []),
    ("AID-WEB-03", P_FINAID, "Sports Scholarships", "Institutional scholarship",
     "This is a 65% tuition-only scholarship for students in sports disciplines that are relevant to the university "
     "sports program needs.", []),
    ("AID-WEB-04", P_FINAID, "First-Time Freshman Scholarship", "Institutional scholarship",
     "This is a 30% scholarship for local and international students.", []),
    ("AID-WEB-05", P_FINAID, "Criminal Justice Studies Scholarship", "Institutional scholarship",
     "This is a 50% tuition-only scholarship to Kenyan civil servants seeking to pursue their Bachelor of Arts in "
     "Criminal Justice Studies at USIU-Africa.", []),
    ("AID-WEB-06", P_FINAID, "Diversity Scholarships", "Institutional scholarship",
     "This is a 100% tuition-only scholarship for qualified applicants from Under-Represented Communities and Persons "
     "with Disability.", []),
    ("AID-WEB-07", P_FINAID, "Vice Chancellor’s Grant", "Institutional grant",
     "This is a 25% tuition-only scholarship for continuing undergraduate students with a cumulative GPA of 3.3 or "
     "better.", []),
    ("AID-WEB-08", P_FINAID, "Special Need Grant", "Institutional grant",
     "The objective of this grant is to help students who have fallen into sudden financial hardships", []),
    ("AID-WEB-09", P_FINAID, "Student Council (SC) Grant", "Institutional grant",
     "This is a combined merit and need-based tuition-only grant introduced by the Student Council for continuing "
     "undergraduate students.", []),
    ("AID-WEB-10", P_FINAID, "Campus Work Opportunity Program (CWOP)", "Work study",
     "This program provides part-time work opportunities for full-time undergraduate and graduate students who "
     "demonstrate financial need.", []),
    ("AID-WEB-11", P_FINAID, "Educate Your Own (EYO)", "Student-led fund",
     "paying 25–50% of their tuition", []),
    ("AID-WEB-12", P_FINAID, "Family Tuition Waiver", "Loyalty programme",
     "Family Tuition Waiver: This is a 10% tuition-only waiver in recognition of parents for their continuous support "
     "for USIU-Africa. At least three siblings must have been or be enrolled at USIU-Africa.", ["W12"]),
    ("AID-WEB-13", P_FINAID, "Alumni Graduate Tuition Waiver", "Loyalty programme",
     "Alumni Graduate Tuition Waiver: This is a 10% tuition-only waiver for USIU-Africa alumni who are pursuing their "
     "graduate studies", []),
    ("AID-WEB-14", P_FINAID, "Legatee Tuition Waiver", "Loyalty programme",
     "Legatee Tuition Waiver: This is a 10% tuition waiver for children of USIU-Africa Alumni.", ["W12"]),
    ("AID-WEB-15", P_COMM, "Family Tuition Waiver (alumni benefits page)", "Loyalty programme",
     "Eligible applicant must have two nuclear family (siblings) members previously or currently enrolled at "
     "USIU-Africa. The Applicant must maintain a cumulative GPA of 2.0 at Undergraduate level and a cumulative GPA of "
     "3.0 at graduate level.", ["W12"]),
    ("AID-WEB-16", P_FINAID, "HELB loans", "External loan",
     "Students of Kenyan nationality at USIU-Africa can apply for loans from HELB as long as they meet the required "
     "criteria.", []),
    ("AID-WEB-17", P_FINAID, "EAC Scholarship Programme (KfW, IUCEA) - Master's", "External scholarship (call closed)",
     "Application Deadline: Thursday, September 10, 2026, not later than 5:00 PM, East African Time", ["W10"]),
    ("AID-WEB-18", P_FINAID, "Scholarship call 2026 (undergraduate)", "Institutional call (closed)",
     "Application Deadline: July 15, 2026", ["W10"]),
    ("AID-WEB-19", P_FINAID, "Exness Fintech Scholarship (Master's)", "Sponsored scholarship (2026 call)",
     "2 Master’s Scholarships (Master of Science in Information Security applicants with a first degree in an IT-related "
     "field and a GPA of 3.0 or above).", ["W10"]),
]

# ======================================================================================
# New issues found in the website pages (W-series). type as in the PDF issues.
# evidence: list of (page_id, quote)
# ======================================================================================
WEB_ISSUES = [
    {"id": "W01", "type": "document_quality", "severity": "medium", "admin_decision": True, "department": "marketing",
     "summary": "Contact Us page: several e-mail links open a different address from the one displayed "
                "(careeroffice@ opens registrar@; helpdesk@, multimedia@ and finance@ open admit@). The dataset records "
                "the displayed address.",
     "evidence": [(P_CONTACT, "Mail: careeroffice@usiu.ac.ke"), (P_CONTACT, "MISMATCH: visible address is careeroffice@, target is registrar@")],
     "action": "Marketing/web team to fix the links. Use the displayed address only after the office confirms it."},
    {"id": "W02", "type": "document_quality", "severity": "medium", "admin_decision": True, "department": "marketing",
     "summary": "Telephone links do not match the numbers displayed: Contact Us admissions line opens +254735295654; "
                "Intake page 'Admissions Officer 1 +254 730 116 503' opens +254730116444 and 'Admissions Officer 2 "
                "+254 730 116 522' opens a mailto to halfmarathon@usiu.ac.ke; Health and Disability pages open "
                "'tel:110220330'.",
     "evidence": [(P_CONTACT, "target number +254735295654 differs from the visible number"),
                  (P_INTAKE, "tel:+254730116444"), (P_HEALTH, "tel:110220330")],
     "action": "Record displayed numbers only; web team to fix links."},
    {"id": "W04", "type": "document_quality", "severity": "medium", "admin_decision": True, "department": "marketing",
     "summary": "Contact Us page prints the Library and Registrar numbers with country code +257 (Burundi) instead of "
                "+254 (Kenya). Recorded exactly as printed; not corrected.",
     "evidence": [(P_CONTACT, "Tel: +257 730 116 429/254/549/294"), (P_CONTACT, "Tel: +257 730 116 786")],
     "action": "Registrar and Library to confirm; web team to correct."},
    {"id": "W05", "type": "inconsistency", "severity": "low", "admin_decision": False, "department": "admissions",
     "summary": "Admissions telephone numbers are given in several different combinations across pages "
                "(290/291 main line; 247/300/397/503/522; and all seven together).",
     "evidence": [(P_CONTACT, "Tel: +254 730 116 247 /300 /397 /503 /522"),
                  (P_ADMREQ, "+254 730 116 290 / 291 / 247 / 300 / 397 / 503 / 522"),
                  (P_INTAKE, "Admissions Main Line +254 730 116 290 /291")],
     "action": "Note only; all are printed on official pages."},
    {"id": "W06", "type": "inconsistency", "severity": "medium", "admin_decision": True, "department": "finance",
     "summary": "Finance telephone numbers differ between pages: Contact Us '+254 730 116 403'; Fee Payment page "
                "'+254 730 116 175/217/189'; Student Accounts '0730116509/221/538/224'; Credit Control '+254 730 116 538'.",
     "evidence": [(P_CONTACT, "Tel: +254 730 116 403"), (P_FEEPAY, "+254 730 116 175/217/189"),
                  (P_FEEPAY, "Finance Department (Student Accounts – 0730116509/221/538/224)")],
     "action": "Finance Office to confirm which numbers students should use."},
    {"id": "W09", "type": "conflict", "severity": "medium", "admin_decision": True, "department": "finance",
     "summary": "Cash and deposit-slip rules differ: Tuition page says 'No cash payments are accepted in the Finance "
                "Office' and to 'forward the deposit slip to the Finance Office'; Fee Payment page says cash above "
                "KES 1,000 is not accepted at the cash office (implying smaller amounts are) and 'No need to bring cash "
                "deposit slips to our cash office'.",
     "evidence": [(P_TUITION, "No cash payments are accepted in the Finance Office."),
                  (P_FEEPAY, "Cash payments in excess of KES 1, 000 are not accepted at the cash office."),
                  (P_FEEPAY, "No need to bring cash deposit slips to our cash office")],
     "action": "Finance Office to confirm. The chatbot should quote both and refer to Finance."},
    {"id": "W10", "type": "outdated", "severity": "medium", "admin_decision": False, "department": "admissions",
     "summary": "Time-limited content still published on 2026-11-01: 'Apply for May 2026' banner on Admission & Fees; "
                "2026 scholarship call (deadline 15 July 2026) and EAC scholarship (deadline 10 September 2026) on "
                "Financial Aid. The Intake page shows the January (Spring) 2027 intake.",
     "evidence": [(P_ADMFEES, "The May 2026 intake to USIU-Africa is now open!"),
                  (P_FINAID, "Application Deadline: July 15, 2026"),
                  (P_INTAKE, "January (Spring) Semester 2027 Intake Ongoing")],
     "action": "Mark these records as expired; never present a passed deadline as open."},
    {"id": "W11", "type": "conflict", "severity": "high", "admin_decision": True, "department": "registrar",
     "summary": "Undergraduate transfer-credit rules differ between two official pages. Admission Requirements: maximum "
                "49% transferable, 51% residency, at most 24 semester units of extension credit. International "
                "Applicants: maximum 90 trimester units, final 30 semester units in residence, at most 23 trimester units "
                "of extension credit. The latter page also mixes semester and trimester units.",
     "evidence": [(P_ADMREQ, "A maximum of 49% of credit earned may be accepted for transfer"),
                  (P_INTL, "A maximum of 90 trimester units of credit earned may be accepted for transfer"),
                  (P_INTL, "No more than 23 trimester units of extension credits")],
     "action": "Registrar/Admissions to confirm the current rule (the Academic Catalog 2024-2026 should be checked)."},
    {"id": "W12", "type": "conflict", "severity": "medium", "admin_decision": True, "department": "financial_aid",
     "summary": "Family Tuition Waiver eligibility differs: Financial Aid page requires at least three siblings and a "
                "CGPA of 2.5 (undergraduate) / 3.2 (graduate); the 2026 Commencement (alumni benefits) page requires "
                "two siblings and a GPA of 2.0 / 3.0. Legatee waiver GPA also differs (2.5/3.2 vs 2.0/3.0).",
     "evidence": [(P_FINAID, "At least three siblings must have been or be enrolled at USIU-Africa."),
                  (P_COMM, "Eligible applicant must have two nuclear family (siblings) members previously or currently "
                           "enrolled at USIU-Africa.")],
     "action": "Financial Aid Office to confirm."},
    {"id": "W13", "type": "conflict", "severity": "medium", "admin_decision": True, "department": "student_affairs",
     "summary": "On-campus accommodation cost: Tuition & Fees 'Room Only 42,000.00' per semester (and a 7-day meal plan "
                "58,800.00); Housing FAQ 'What is the cost of accommodation on campus? KES. 30,000' (period not stated).",
     "evidence": [(P_TUITION, "| Room Only | 42,000.00 |"), (P_HOUSING, "What is the cost of accommodation on campus? KES. 30,000")],
     "action": "Housing Office/Finance to confirm. The 2026-2027 fee schedule (42,000) is the more specific source."},
    {"id": "W14", "type": "conflict", "severity": "high", "admin_decision": True, "department": "admissions",
     "summary": "English proficiency (TOEFL) minimums differ: website Admission Requirements 'TOEFL iBT 79 or higher, "
                "current within two years'; Student Handbook 'TOEFL 550 (213 computer-based or 90 Internet-based)'; "
                "programme pages for IST and Applied Computer Technology '550 or higher (213 computer based)'.",
     "evidence": [(P_ADMREQ, "score of 79 or higher in the Internet Based)"),
                  ("programs__bachelor-of-science-in-information-systems-technology", "550 or higher (213 computer based)")],
     "action": "Admissions to confirm; see also V16."},
    {"id": "W15", "type": "document_quality", "severity": "low", "admin_decision": False, "department": "marketing",
     "summary": "Vision, Mission & Values page repeats the 'Life Long Learning' description under 'Academic freedom'. "
                "The handbook (page 7) gives the Academic freedom text 'Upholding the spirit of free and critical "
                "thought and enquiry...'. The website text for this value is treated as a web error, not a new value.",
     "evidence": [(P_VMV, "Academic freedom")],
     "action": "Use the handbook wording for Academic freedom; report the web error."},
    {"id": "W16", "type": "inconsistency", "severity": "low", "admin_decision": False, "department": "marketing",
     "summary": "Diversity figures differ: 'over 70 nationalities' (About Us intro, FAQ) vs 'students from over 60 "
                "countries' (About Us) vs 'More than sixty nationalities' (Intake page).",
     "evidence": [(P_ABOUT, "we serve students from over 70 nationalities"), (P_ABOUT, "drawn students from over 60 countries"),
                  (P_INTAKE, "More than sixty nationalities.")],
     "action": "Quote with source; do not merge."},
    {"id": "W17", "type": "inconsistency", "severity": "low", "admin_decision": False, "department": "academic_programmes",
     "summary": "School name varies: 'School of Communication and Creative Arts' (Our Schools page) vs 'School of "
                "Communication, Cinematic and Creative Arts' (programme pages, handbook) vs 'School of Communications, "
                "Cinematic and Creative Arts - SCCCA' (Tuition page).",
     "evidence": [(P_SCHOOLS, "School of Communication and Creative Arts")],
     "action": "Note only."},
    {"id": "W18", "type": "document_quality", "severity": "medium", "admin_decision": True, "department": "academic_programmes",
     "summary": "Programme pages contain apparent copy/paste errors that affect requirements: MA Criminal and "
                "Transitional Justice requires 'a background in a business field'; MA International Relations (Online) "
                "contains an editorial note '(Check the information on the website so that it reflects this)' and two "
                "different prerequisite lists; MA Communication Studies (Online) lists KCSE-level entry requirements for "
                "a master's degree; MSc Data Science (Online) FAQ lists undergraduate entry requirements; the "
                "Psychology page URL says 'bachelor-of-science' but the title is 'Bachelor of Arts'.",
     "evidence": [("programs__master-of-arts-in-criminal-and-transitional-justice", "with a background in a business field"),
                  ("programs__master-of-arts-in-international-relations-online",
                   "(Check the information on the website so that it reflects this)"),
                  ("programs__master-of-arts-in-communication-studies-online", "C+ for the Kenya Certificate of Secondary "
                                                                               "Education (KCSE) holders")],
     "action": "Schools/Admissions to confirm programme requirements before they are shown as fact."},
    {"id": "W19", "type": "inconsistency", "severity": "medium", "admin_decision": True, "department": "academic_programmes",
     "summary": "Programmes on the 2026-2027 fee page have no programme page or listing (Bachelor of Global Leadership & "
                "Governance; BA Sociology; BSc Clinical Pharmacology and Therapeutics; BSc Epidemiology and "
                "Biostatistics; BTech Analytical Chemistry; BSc Applied Biochemistry), and the MSc Clinical Pharmacology "
                "Therapeutics programme page has no fee table.",
     "evidence": [(P_TUITION, "Bachelor of Global Leadership & Governance"), (P_TUITION, "Bachelor of Arts in Sociology"),
                  ("academics__masters-programs", "Master Of Science In Clinical Pharmacology Therapeutics")],
     "action": "Admissions/Schools to confirm which programmes are open for application."},
    {"id": "W21", "type": "ambiguity", "severity": "low", "admin_decision": False, "department": "finance",
     "summary": "Online MSc Data Science & Analytics fee table charges 'Technology Fee 6,000.00', while the fee note says "
                "all students pay a 3,500 Technology fee and IT courses pay a 6,000 IT Lab fee.",
     "evidence": [(P_TUITION, "Online Master of Science in Data Science & Analytics")],
     "action": "Quote as printed."},
    {"id": "W22", "type": "ambiguity", "severity": "low", "admin_decision": False, "department": "academic_programmes",
     "summary": "MBA (Online): overview says 'Delivered online over 5 semesters (about 18 months)'; the duration field "
                "says '2 Years'.",
     "evidence": [("programs__master-of-business-administration-online", "Delivered online over 5 semesters (about 18 months)")],
     "action": "Quote both."},
    {"id": "W23", "type": "missing_source", "severity": "high", "admin_decision": True, "department": "admissions",
     "summary": "Doctoral programme pages (DBA, PhD IST, PhD IR, PsyD) and the MA Counseling Psychology (Online) page do "
                "not state admission requirements.",
     "evidence": [("programs__doctor-of-business-administration", "Doctor of Business Administration")],
     "action": "Admissions / School of Graduate Studies to provide requirements."},
    {"id": "W24", "type": "inconsistency", "severity": "low", "admin_decision": False, "department": "admissions",
     "summary": "EXTERNAL (KUCCPS): the KUCCPS homepage says 'Currently, KUCCPS does not place students to the private "
                "colleges', while its FAQ says 'KUCCPS also places students to private universities'. Neither page names "
                "USIU-Africa.",
     "evidence": [("kuccps.net__home", "Currently, KUCCPS does not place students to the private colleges."),
                  ("kuccps.net__frequently-asked-questions", "KUCCPS also places students to private universities.")],
     "action": "Do not tell users whether USIU-Africa admits KUCCPS-placed students; refer to Admissions."},
    {"id": "W25", "type": "ambiguity", "severity": "low", "admin_decision": False, "department": "registrar",
     "summary": "The Academic Calendar page shows the 2026-2027 calendar first and then a heading 'Current' above the "
                "2025-2026 calendar, while the document page labels 2026-2027 as '(Current)'.",
     "evidence": [(P_CAL, "View Academic Calendar 2025 - 2026"), ("documents__academic-calendar-2026-2027", "Academic Calendar 2026 – 2027 (Current)")],
     "action": "Treat 2026-2027 as current (its document page says so); note only."},
    {"id": "W26", "type": "conflict", "severity": "high", "admin_decision": True, "department": "finance",
     "summary": "ABSA account details differ: website 'Branch Name: Sarit', 'Branch Code: 106', with a USD account "
                "2047249840 (intermediary Citi Bank, New York); calendar 2026-2027 'Westlands', 'Branch Code: 073'; "
                "handbook 'Westlands'. Same KES account number 2037727558 in all three.",
     "evidence": [(P_FEEPAY, "USD Account Number: 2047249840"), (P_FEEPAY, "Sarit")],
     "action": "Finance Office to confirm. Never present bank details as confirmed."},
]

# Updates to the Stage 2 issues from the website evidence. status: resolved | partially_resolved | unresolved
# | updated (new evidence, still open)
ISSUE_UPDATES = {
    "V01": ("partially_resolved", [(P_FEEPAY, "NCBA BANK KENYA LTD")],
            "The official Fee Payment & Refunds page (sitemap lastmod 2026-04-01; publication date not stated) gives a "
            "newer list of six banks. The handbook list (May 2024) should be treated as superseded, but the website and "
            "the 2026-2027 calendar still differ (see V02, W26). Finance confirmation is still required."),
    "V02": ("updated", [(P_FEEPAY, "STANBIC BANK KENYA")],
            "Stanbic Bank accounts (KES 0100011682469, USD 0100011682523) also appear on the official Fee Payment & "
            "Refunds page, so they are not handbook-only. They are still absent from the 2026-2027 calendar list."),
    "V03": ("partially_resolved", [(P_FEEPAY, "A/C NAME: USIU or U.S International University")],
            "The website agrees with the 2026-2027 calendar: bank 'NCBA BANK KENYA LTD', account name 'USIU or U.S "
            "International University', and adds Bank Code 07 / Branch Code 000. Two current official sources agree; "
            "the handbook's 'Commercial Bank of Africa' naming is the older version. Routing number 021000021 appears "
            "only in the handbook."),
    "V04": ("unresolved", [(P_FEEPAY, "Only graduating or exiting students shall be refunded.")],
            "The website describes refund applications for exiting students but does not state the drop-course charge "
            "waiver schedule, so the 14-day (handbook) vs calendar-date conflict remains."),
    "V05": ("resolved", [(P_CATALOG, "Download Academic Catalog 2024 - 2026")],
            "The official Academic Catalog page links the 'Academic Catalog 2024 - 2026'; the handbook's 2021-2023 link "
            "is outdated. (The 2024-2026 catalog itself was not downloaded or extracted.)"),
    "V07": ("unresolved", [], "No dated handbook edition is published on the pages collected; the candidate handbook URL "
                              "returns HTTP 404."),
    "V12": ("partially_resolved", [(P_HEALTH, "+254 730 116 760 /761 /762 /271")],
            "The website Health & Wellness page gives emergency numbers +254 730 116 760 /761 /762 /271 and "
            "+254 798 294 538. These agree with the handbook's 760/762/271 (pages 50-51) and do not include 720 "
            "(page 24)."),
    "V13": ("partially_resolved", [(P_HEALTH, "Phone: +254-730 116 748/746/750/791/797/817"),
                                   (P_CONTACT, "Tel: 0730 116 778 /779 /796")],
            "Website counselling numbers are 748/746/750/791/797/817 (790 is not listed). Extension 779 is listed for "
            "Placement and Careers on the Contact Us page, matching handbook page 24, so 'Counselling and Health Centre "
            "(extension 779)' on handbook page 54 looks wrong."),
    "V14": ("partially_resolved", [(P_COMM, "University Security: 0730 116 266 / 0730 116 461")],
            "The 2026 Commencement page lists University Security as 0730 116 266 / 0730 116 461, which matches the "
            "first number on handbook page 24; handbook page 54 (730116 774/618) is not confirmed."),
    "V16": ("updated", [(P_ADMREQ, "score of 79 or higher in the Internet Based)")],
            "Now a three-way conflict (see W14): website TOEFL iBT 79 (current within two years), handbook 550/213/90, "
            "programme pages 550/213."),
    "V17": ("unresolved", [(P_COMM, "Saturday, September 26 - Graduation Date")],
            "The 48th Commencement took place on Saturday, 26 September 2026 (the page states the year in its security "
            "advisory). The page does not say which graduation Fall 2026 completers belong to."),
    "V20": ("unresolved", [(P_CAL, "View Academic Calendar 2026 - 2027")],
            "The calendar PDF published on the website is byte-identical to the local copy, so the 'September 16 "
            "Friday' error is in the official published calendar."),
    "V22": ("resolved", [("documents__academic-calendar-2026-2027", "Academic Calendar 2026 – 2027 (Current)")],
            "Official URL confirmed: https://www.usiu.ac.ke/wp-content/uploads/2026/04/Academic-Calendar-2026-2027.pdf "
            "(landing page https://www.usiu.ac.ke/documents/academic-calendar-2026-2027/). The downloaded file has the "
            "same SHA-256 as the local PDF."),
    "V23": ("unresolved", [], "Candidate URL https://www.usiu.ac.ke/assets/file/266ac45d-student-handbook.pdf returned "
                              "HTTP 404 on 2026-11-01. No other public handbook link was found."),
    "V24": ("resolved", [], "Verified against the PDF itself using text positions (validation_reports/"
                            "layout_verification.json): each heading on page 7 sits directly above the block assigned "
                            "to it."),
    "V26": ("partially_resolved", [(P_CONTACT, "Mail: registrar@usiu.ac.ke")],
            "The website Contact Us page prints registrar@usiu.ac.ke; the calendar's 'registra@usiu.ac.ke' is probably a "
            "typing error. Both are kept as printed."),
    "V28": ("unresolved", [(P_FEEPAY, "interest charge of 1.5% per month on any outstanding debit balance from the 2nd day")],
            "The website agrees on the rate and start (2nd day of the semester) but does not say how long interest runs."),
    "V32": ("updated", [(P_FEEPAY, "MUS – Mr. and Miss USIU-Africa Payment")],
            "The website lists the MUS purpose code with the standard paybill and no separate account number."),
}
