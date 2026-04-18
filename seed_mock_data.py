from accounts.models import User, Business, HRProfile
from citizens.models import CitizenProfile
from institutions.models import Institution, InstitutionProfile, CertificateRecord

PWD = "Pass@12345"

def unique_username(base):
    username = base
    counter = 1
    while User.objects.filter(username=username).exclude(email__iexact=base).exists():
        username = f"{base}{counter}"
        counter += 1
    return username

universities = [
    ("University of Nairobi", "UON", "registrar@uonbi.ac.ke"),
    ("Kenyatta University", "KU", "registrar@ku.ac.ke"),
    ("Moi University", "MOI", "registrar@moi.ac.ke"),
    ("Jomo Kenyatta University of Agriculture and Technology", "JKUAT", "registrar@jkuat.ac.ke"),
    ("Strathmore University", "SU", "registrar@strathmore.edu"),
]

colleges = [
    ("Kenya Medical Training College", "KMTC", "dean@kmtc.ac.ke"),
    ("Kenya Institute of Management", "KIM", "dean@kim.ac.ke"),
    ("Kenya Technical Trainers College", "KTTC", "dean@kttc.ac.ke"),
]

businesses = [
    ("Safaricom PLC", "SAF"),
    ("Equity Bank Kenya", "EQTY"),
    ("KCB Group", "KCBG"),
    ("Co-operative Bank of Kenya", "COOP"),
    ("Kenya Airways", "KQ"),
    ("Nation Media Group", "NMG"),
    ("Bamburi Cement", "BAMB"),
    ("East African Breweries Ltd", "EABL"),
    ("KenGen", "KENGEN"),
    ("Kenya Power", "KPLC"),
]

citizen_seed = [
    ("30000001", "john.mutua@example.com", "John", "Mutua"),
    ("30000002", "mary.wanjiku@example.com", "Mary", "Wanjiku"),
    ("30000003", "kevin.otieno@example.com", "Kevin", "Otieno"),
    ("30000004", "fatma.ali@example.com", "Fatma", "Ali"),
    ("30000005", "david.kamau@example.com", "David", "Kamau"),
    ("30000006", "susan.njeri@example.com", "Susan", "Njeri"),
    ("30000007", "ian.odhiambo@example.com", "Ian", "Odhiambo"),
    ("30000008", "jane.atieno@example.com", "Jane", "Atieno"),
    ("30000009", "paul.ndungu@example.com", "Paul", "Ndungu"),
    ("30000010", "musa.hassan@example.com", "Musa", "Hassan"),
    ("30000011", "lucy.chebet@example.com", "Lucy", "Chebet"),
    ("30000012", "peter.kiptoo@example.com", "Peter", "Kiptoo"),
    ("30000013", "caroline.nasubo@example.com", "Caroline", "Nasubo"),
    ("30000014", "brian.maina@example.com", "Brian", "Maina"),
    ("30000015", "grace.nasambu@example.com", "Grace", "Nasambu"),
    ("30000016", "elvis.barasa@example.com", "Elvis", "Barasa"),
    ("30000017", "felix.okello@example.com", "Felix", "Okello"),
    ("30000018", "margaret.nduta@example.com", "Margaret", "Nduta"),
    ("30000019", "george.mwangi@example.com", "George", "Mwangi"),
    ("30000020", "edith.kemboi@example.com", "Edith", "Kemboi"),
    ("30000021", "robert.kariuki@example.com", "Robert", "Kariuki"),
    ("30000022", "salma.omar@example.com", "Salma", "Omar"),
    ("30000023", "moses.mutuku@example.com", "Moses", "Mutuku"),
    ("30000024", "agnes.chepkorir@example.com", "Agnes", "Chepkorir"),
    ("30000025", "victor.muriuki@example.com", "Victor", "Muriuki"),
    ("30000026", "peris.nyambura@example.com", "Peris", "Nyambura"),
    ("30000027", "kennedy.kinyua@example.com", "Kennedy", "Kinyua"),
    ("30000028", "mercy.nyambane@example.com", "Mercy", "Nyambane"),
    ("30000029", "patrick.lel@example.com", "Patrick", "Lel"),
    ("30000030", "sarah.ndegwa@example.com", "Sarah", "Ndegwa"),
    ("30000031", "joshua.lagat@example.com", "Joshua", "Lagat"),
    ("30000032", "lynn.muthoni@example.com", "Lynn", "Muthoni"),
    ("30000033", "amos.nyongesa@example.com", "Amos", "Nyongesa"),
    ("30000034", "cynthia.korir@example.com", "Cynthia", "Korir"),
    ("30000035", "eric.gakuru@example.com", "Eric", "Gakuru"),
    ("30000036", "sharon.onyango@example.com", "Sharon", "Onyango"),
    ("30000037", "diana.mutheu@example.com", "Diana", "Mutheu"),
    ("30000038", "collins.abdi@example.com", "Collins", "Abdi"),
    ("30000039", "hope.naliaka@example.com", "Hope", "Naliaka"),
    ("30000040", "allan.kipsang@example.com", "Allan", "Kipsang"),
]

inst_admin_map = {}
for name, code, admin_email in universities + colleges:
    base_username = admin_email.split("@")[0]
    username = unique_username(base_username)
    inst, _ = Institution.objects.get_or_create(name=name, defaults={"code": code})
    admin_user, created = User.objects.get_or_create(
        email=admin_email,
        defaults={"username": username, "role": User.Role.INSTITUTION_ADMIN, "first_name": name.split()[0], "last_name": "Admin"},
    )
    if created:
        admin_user.set_password(PWD)
        admin_user.save()
    InstitutionProfile.objects.get_or_create(user=admin_user, institution=inst)
    inst_admin_map[inst.id] = admin_user

for name, code in businesses:
    biz, _ = Business.objects.get_or_create(name=name, defaults={"code": code})
    hr_email = f"hr_{code.lower()}@demo.local"
    base_username = hr_email.split("@")[0]
    hr_user, created = User.objects.get_or_create(
        email=hr_email,
        defaults={"username": unique_username(base_username), "role": User.Role.HR_MANAGER, "first_name": name.split()[0], "last_name": "HR"},
    )
    if created:
        hr_user.set_password(PWD)
        hr_user.save()
    HRProfile.objects.get_or_create(user=hr_user, business=biz)

citizen_profiles = []
for nid, email, first, last in citizen_seed:
    base_username = email.split("@")[0]
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": unique_username(base_username), "role": User.Role.CITIZEN, "first_name": first, "last_name": last},
    )
    if created:
        user.set_password(PWD)
        user.save()
    cp, _ = CitizenProfile.objects.get_or_create(user=user, national_id=nid, defaults={"otp_email": email})
    citizen_profiles.append(cp)

programs = [
    ("BSc Computer Science", "Bachelor", "Second Class Upper"),
    ("BCom Finance", "Bachelor", "First Class"),
    ("BSc Electrical Engineering", "Bachelor", "Second Class Upper"),
    ("BA Economics", "Bachelor", "Second Class Lower"),
    ("Diploma in IT", "Diploma", "Distinction"),
    ("Diploma in HRM", "Diploma", "Credit"),
    ("Diploma in Project Management", "Diploma", "Credit"),
    ("MBA Strategic Management", "Masters", "Credit"),
    ("MSc Data Science", "Masters", "Credit"),
]

inst_ids = list(inst_admin_map.keys())
prog_cycle = programs * 5

for idx, cp in enumerate(citizen_profiles):
    inst_id = inst_ids[idx % len(inst_ids)]
    inst_admin = inst_admin_map[inst_id]
    inst = Institution.objects.get(id=inst_id)
    cert_name, level, grade = prog_cycle[idx % len(prog_cycle)]
    grad_year = 2010 + (idx % 14)
    CertificateRecord.objects.get_or_create(
        national_id=cp.national_id,
        institution=inst,
        certificate_name=cert_name,
        award_level=level,
        grade=grade,
        graduation_year=grad_year,
        full_name=f"{cp.user.first_name} {cp.user.last_name}",
        defaults={"registration_number": "", "created_by": inst_admin},
    )

print("Seed complete: 5 universities, 3 colleges, 10 businesses, 40 citizens. Default password:", PWD)
