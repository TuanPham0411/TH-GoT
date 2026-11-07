"""One vocabulary for child stages, server difficulty and retained legacy sessions."""
STAGES = {
 'kindergarten-3': {'title':'Mẫu giáo bé · 3–4 tuổi','grade':0,'age':'3–4','limit':3,'band':0,'minutes':10,'focus':'Nhận biết bằng giác quan, đếm đến 3, gọi tên cảm xúc và chơi cùng người lớn.'},
 'kindergarten-4': {'title':'Mẫu giáo nhỡ · 4–5 tuổi','grade':0,'age':'4–5','limit':5,'band':0,'minutes':10,'focus':'So sánh nhóm đến 5, tìm quy luật đơn giản, kể việc theo thứ tự và biết thay lượt.'},
 'kindergarten-5': {'title':'Mẫu giáo lớn · 5–6 tuổi','grade':0,'age':'5–6','limit':10,'band':0,'minutes':10,'focus':'Đếm đến 10, nghe âm và vần, làm theo trình tự, chuẩn bị tự lập vào lớp Một.'},
 'grade-1': {'title':'Lớp 1 · 6–7 tuổi','grade':1,'age':'6–7','limit':20,'band':1,'minutes':10,'focus':'Cộng trừ trong phạm vi 20, đọc câu ngắn, hiểu giờ đúng và nếp sinh hoạt.'},
 'grade-2': {'title':'Lớp 2 · 7–8 tuổi','grade':2,'age':'7–8','limit':1000,'band':1,'minutes':20,'focus':'Số đến 1000, bước đầu nhân chia 2 và 5, đọc hiểu đoạn ngắn và đo độ dài.'},
 'grade-3': {'title':'Lớp 3 · 8–9 tuổi','grade':3,'age':'8–9','limit':1000,'band':2,'minutes':20,'focus':'Tính toán với số lớn hơn, giải thích từ dữ kiện, quan sát tự nhiên và ghi chép.'},
 'grade-4': {'title':'Lớp 4 · 9–10 tuổi','grade':4,'age':'9–10','limit':10000,'band':3,'minutes':20,'focus':'Phân số, chu vi và diện tích, đọc có suy luận, lập kế hoạch và kiểm chứng.'},
 'grade-5': {'title':'Lớp 5 · 10–11 tuổi','grade':5,'age':'10–11','limit':100000,'band':3,'minutes':20,'focus':'Số thập phân, tỉ số phần trăm, thể tích, vận tốc và thiết kế giải pháp có lý do.'},
}
PROFILES={key:value['title'] for key,value in STAGES.items()}
LEGACY={'preschool':['kindergarten-3','kindergarten-4','kindergarten-5'], 'early-primary':['grade-1','grade-2'], 'middle-primary':['grade-3'], 'upper-primary':['grade-4','grade-5']}

def canonical(profile):
 if not isinstance(profile,str):return None
 return {'preschool':'kindergarten-4','early-primary':'grade-1','middle-primary':'grade-3','upper-primary':'grade-4'}.get(profile,profile)

def expand(profiles):
 return list(dict.fromkeys(stage for profile in profiles for stage in LEGACY.get(profile,[profile]) if stage in STAGES))

def allowed(profiles,profile):
 return canonical(profile) in expand(profiles)
