"""Editorial curriculum and short, original retellings of public-domain tales."""
import json
from pathlib import Path
PROFILES={'preschool':'Mẫu giáo · 3–5 tuổi','early-primary':'Lớp 1–2 · 6–7 tuổi','middle-primary':'Lớp 3 · 8 tuổi','upper-primary':'Lớp 4–5 · 9–11 tuổi'}
SUBJECTS={'numbers':'Xứ sở toán học','language':'Vườn tiếng Việt','science':'Phòng khám phá','life':'Thành phố tử tế','logic':'Đảo tư duy','creative':'Xưởng sáng tạo'}
# id, title, subject, mechanic, youngest group (0–3), goal, short lesson, family extension
ROWS=[
('count-garden','Vườn đếm hạt','numbers','count',0,'Đếm từng vật và nối với số.','Chạm vào từng hạt, mỗi hạt chỉ đếm một lần. Số cuối cùng là số hạt có tất cả.','Xếp thìa đủ cho từng người trong bữa cơm.'),
('compare-baskets','Giỏ nào nhiều hơn?','numbers','compare',0,'So sánh hai nhóm đồ vật.','Ghép mỗi quả bên trái với một quả bên phải. Bên còn quả dư có nhiều hơn.','So sánh hai nhóm cúc áo cùng người lớn.'),
('add-market','Chợ cộng vui','numbers','add',1,'Gộp hai nhóm để tìm tổng.','Cộng là gộp thêm. Có 3 quả, thêm 2 quả thì đếm tiếp 4, 5.','Dùng nắp chai minh họa phép cộng.'),
('subtract-train','Chuyến tàu bớt đi','numbers','subtract',1,'Hiểu bớt đi và tìm phần còn lại.','Trừ là lấy bớt một phần. Kiểm tra bằng cách cộng phần đã bớt với phần còn lại.','Kể chuyện lấy bớt vài chiếc bút khỏi hộp.'),
('multiply-orchard','Vườn cây theo hàng','numbers','multiply',2,'Nhận ra các nhóm có số lượng bằng nhau.','Ba hàng, mỗi hàng bốn cây: 4 + 4 + 4 = 3 × 4 = 12.','Xếp vật nhỏ thành các hàng bằng nhau.'),
('divide-picnic','Chia bánh dã ngoại','numbers','divide',2,'Chia đều cho các nhóm.','Phát lần lượt mỗi bạn một chiếc cho đến hết. Các bạn phải nhận số lượng bằng nhau.','Chia đều 12 khối gỗ cho 3 bạn đồ chơi.'),
('fraction-kitchen','Bếp phân số','numbers','fraction',2,'Nhận biết phần bằng nhau của một hình.','Một nửa là một trong hai phần bằng nhau. Một phần tư là một trong bốn phần bằng nhau.','Gấp tờ giấy thành hai rồi bốn phần bằng nhau.'),
('clock-town','Thành phố đồng hồ','numbers','clock',1,'Đọc giờ đúng trên đồng hồ.','Kim ngắn chỉ giờ. Khi kim dài ở số 12, ta đọc giờ đúng.','Tìm đồng hồ ở nhà và kể một việc làm vào giờ đó.'),
('money-shop','Cửa hàng tiết kiệm','numbers','money',2,'Tính tiền hàng và tiền trả lại.','Tiền trả lại bằng số tiền đưa trừ giá món hàng. Hãy kiểm tra phép tính trước khi trả lời.','Chơi bán hàng bằng tiền giấy tự vẽ.'),
('measure-lab','Phòng đo lường','numbers','measure',2,'Đổi đơn vị độ dài và khối lượng cơ bản.','Một mét bằng 100 xăng-ti-mét; một ki-lô-gam bằng 1000 gam. Chỉ đổi giữa các đơn vị cùng đại lượng.','Dùng thước đo một quyển vở và ghi đơn vị.'),
('number-line','Đường tàu số','numbers','numberline',1,'Tìm số còn thiếu trên dãy số.','Quan sát khoảng cách giữa hai số liên tiếp trước khi điền. Không phải dãy nào cũng tăng từng đơn vị.','Vẽ một đường số và đặt quân cờ lên các vị trí.'),
('word-problems','Nhà thám hiểm toán','numbers','wordmath',3,'Chọn phép tính từ một tình huống thực tế.','Đọc điều đã biết, nói điều cần tìm rồi chọn cách tính. Viết câu trả lời kèm đơn vị.','Tự đặt một bài toán về số trang sách đã đọc.'),
('vowel-orchard','Vườn nguyên âm','language','vowel',0,'Nhận diện các nguyên âm tiếng Việt.','A, Ă, Â, E, Ê, I, O, Ô, Ơ, U, Ư, Y là các chữ ghi nguyên âm. Đọc chậm và quan sát hình chữ.','Tìm chữ a hoặc o trên bìa sách.'),
('tone-bridge','Cầu vồng dấu thanh','language','tone',1,'Phân biệt từ thay đổi theo dấu thanh.','Dấu thanh làm thay đổi cách đọc và nghĩa: ba, bà, bá, bả, bã, bạ. Hãy đọc cả từ.','Cùng người lớn tìm các từ có dấu hỏi và dấu ngã.'),
('word-order','Xếp câu cùng bạn','language','sentence',1,'Sắp xếp các cụm từ thành câu có nghĩa.','Một câu kể cho biết ai hoặc cái gì và đang làm gì. Đọc lại cả câu để kiểm tra.','Viết một câu về việc tốt vừa làm.'),
('rhyme-river','Dòng sông vần điệu','language','rhyme',1,'Nghe và nhận ra vần giống nhau.','Đọc rõ phần vần: mèo và trèo cùng có vần eo. Nhìn cả chữ và nghe âm thanh.','Cùng nhau nghĩ hai từ có vần an.'),
('read-and-understand','Đọc và tìm điều đúng','language','reading',2,'Tìm thông tin có trong một đoạn văn.','Đọc câu hỏi, quay lại đoạn văn tìm bằng chứng. Không đoán điều đoạn văn không nói.','Đọc một đoạn truyện và kể lại bằng lời của mình.'),
('punctuation','Bưu điện dấu câu','language','punctuation',2,'Dùng dấu chấm và dấu hỏi đúng chỗ.','Câu hỏi kết thúc bằng dấu hỏi. Câu kể kết thúc bằng dấu chấm. Đọc lên để nghe ý câu.','Viết một câu hỏi muốn hỏi ông bà.'),
('synonym','Kho báu từ gần nghĩa','language','synonym',3,'Nhận biết từ gần nghĩa trong ngữ cảnh.','Hai từ gần nghĩa có thể cùng diễn tả một ý nhưng sắc thái khác nhau. Luôn đọc trong câu.','Tìm hai cách khen một người chăm chỉ.'),
('antonym','Cánh cửa đối nghĩa','language','antonym',1,'Ghép những từ có nghĩa đối nhau.','Cao và thấp, nóng và lạnh diễn tả hai phía đối lập. Một từ có thể cần ngữ cảnh rõ ràng.','Tìm đồ vật dài và ngắn trong phòng.'),
('seed-journey','Hành trình của hạt','science','growth',0,'Sắp xếp các bước cây lớn lên.','Hạt gặp nước và điều kiện phù hợp sẽ nảy mầm, mọc rễ, ra lá rồi lớn thành cây.','Gieo đậu cùng người lớn; quan sát mỗi ngày, không nếm hạt thử nghiệm.'),
('water-cycle','Chuyến đi của giọt nước','science','watercycle',2,'Hiểu vòng tuần hoàn nước đơn giản.','Nước bốc hơi, hơi nước ngưng tụ thành giọt, mưa rơi xuống rồi nước lại tụ về sông hồ.','Quan sát giọt nước bên ngoài cốc lạnh cùng người lớn.'),
('animal-homes','Ai sống ở đâu?','science','habitat',0,'Ghép sinh vật với môi trường phù hợp.','Sinh vật cần nơi có thức ăn, nước và điều kiện sống phù hợp. Giữ môi trường sạch giúp chúng khỏe mạnh.','Quan sát chim từ xa; không bắt hay cho ăn tùy tiện.'),
('science-sort','Hộp phân loại','science','classify',1,'Phân nhóm theo đặc điểm chung.','Chọn một tiêu chí rõ ràng rồi phân loại. Cùng một vật có thể thuộc các nhóm khác nhau khi tiêu chí đổi.','Phân loại đồ chơi theo chất liệu hoặc công dụng.'),
('weather-station','Trạm thời tiết nhỏ','science','weather',0,'Chọn trang phục và cách ứng xử theo thời tiết.','Quan sát thời tiết trước khi ra ngoài. Mưa cần áo mưa; nắng cần mũ và nước uống.','Vẽ ký hiệu thời tiết hôm nay.'),
('space-observer','Đài quan sát bầu trời','science','space',2,'Phân biệt Mặt Trời, Trái Đất và Mặt Trăng.','Trái Đất quay quanh Mặt Trời; Mặt Trăng quay quanh Trái Đất. Không nhìn trực tiếp vào Mặt Trời.','Quan sát hình dạng Mặt Trăng vào buổi tối cùng người lớn.'),
('float-or-sink','Nổi hay chìm?','science','float',1,'Dự đoán rồi kiểm tra bằng quan sát.','Dự đoán là ý kiến trước khi thử. Kết quả cần dựa trên quan sát, không phải đoán đúng mới giỏi.','Thử vật lớn, sạch trong chậu nông với người lớn; không dùng vật nhọn hay đồ điện.'),
('five-senses','Năm giác quan','science','senses',0,'Gọi tên giác quan dùng để nhận biết.','Mắt nhìn, tai nghe, mũi ngửi, lưỡi nếm, da cảm nhận. Không nếm hoặc ngửi sát chất lạ.','Nhắm mắt nghe ba âm thanh an toàn quanh nhà.'),
('healthy-plate','Đĩa ăn cầu vồng','life','nutrition',1,'Nhận ra bữa ăn cần đa dạng.','Cơ thể cần nhiều nhóm thực phẩm và nước. Không có một món duy nhất thay thế mọi nhóm; dị ứng cần hỏi người lớn.','Cùng người lớn gọi tên các nhóm món trong bữa ăn.'),
('emotion-garden','Khu vườn cảm xúc','life','emotion',0,'Nhận diện cảm xúc và cách bình tĩnh.','Mọi cảm xúc đều có thể được nói ra. Hít thở chậm, gọi tên cảm xúc và tìm người lớn khi cần.','Nói: Con thấy… vì… Con cần…'),
('kindness-town','Thành phố tử tế','life','kindness',0,'Chọn hành động biết quan tâm.','Hỏi trước khi giúp, lắng nghe và tôn trọng câu trả lời của bạn. Giúp đỡ không có nghĩa phải bỏ qua sự an toàn.','Làm một việc tử tế rồi kể lại cảm giác của mình.'),
('road-safety','Đường đến trường','life','roads',1,'Nhận biết hành vi an toàn khi đi đường.','Dừng ở mép đường, đi cùng người lớn, quan sát và theo tín hiệu. Vạch qua đường không thay thế việc quan sát.','Cùng người lớn nhận biết lối đi bộ trên đường quen thuộc.'),
('digital-safety','Hộ chiếu số','life','digital',2,'Biết hỏi người lớn và giữ thông tin riêng.','Không gửi địa chỉ, trường học, mật khẩu hay hình riêng cho người lạ. Nội dung làm con khó chịu thì dừng và nhờ người lớn.','Thực hành câu: Con muốn hỏi bố mẹ trước.'),
('green-city','Thành phố xanh','life','recycle',1,'Giảm lãng phí và phân loại rác theo địa phương.','Dùng lại đồ còn tốt, tiết kiệm nước. Rác nguy hiểm như pin phải giao cho người lớn xử lý.','Cùng người lớn tìm điểm thu gom pin của địa phương.'),
('daily-routine','Một ngày của bé','life','routine',0,'Xếp các bước một việc thường ngày.','Làm từng bước giúp ta tự lập hơn. Có thể nhờ người lớn giúp ở bước chưa làm được.','Tự chuẩn bị cặp sách với bảng kiểm có hình.'),
('ask-for-help','Đội cứu hộ nhỏ','life','help',1,'Biết tìm người lớn đáng tin khi gặp khó khăn.','Khi nguy hiểm: rời xa nếu an toàn, gọi người lớn và nói rõ chuyện. Không tự thử xử lý điện, lửa hay thuốc.','Cùng gia đình chọn những người lớn có thể nhờ giúp.'),
('pattern-trail','Đường mòn quy luật','logic','pattern',0,'Tìm quy luật lặp lại.','Đọc to từng hình trong dãy. Tìm nhóm nhỏ lặp lại rồi đoán hình tiếp theo.','Tạo một dãy màu bằng khối xếp hình.'),
('coding-robot','Robot đi học','logic','robot',2,'Lập chuỗi lệnh và kiểm tra từng bước.','Robot làm đúng lệnh, không tự đoán ý. Chạy thử từng bước; sửa lệnh là một phần của lập trình.','Vẽ lưới trên giấy và chỉ đường cho một đồ chơi.'),
('logic-detective','Thám tử suy luận','logic','deduction',2,'Kết hợp hai dữ kiện để kết luận.','Gạch bỏ điều không thể đúng. Kết luận phải phù hợp với tất cả dữ kiện đã cho.','Chơi đoán đồ vật bằng ba gợi ý.'),
('sequence-cook','Đầu bếp theo bước','logic','recipe',1,'Sắp xếp công việc theo thứ tự hợp lý.','Chuẩn bị trước khi làm; việc sau dựa trên kết quả việc trước. Bếp nóng và dao dành cho người lớn.','Xếp các bước làm bánh mì nguội cùng người lớn.'),
('number-pattern','Mật mã dãy số','logic','numberpattern',2,'Tìm quy luật tăng đều của dãy số.','So sánh hiệu giữa các số liên tiếp, rồi kiểm tra quy luật với cả dãy.','Tạo dãy số cách đều cho người thân đoán.'),
('fraction-compare','Cân bằng phân số','logic','fractioncompare',3,'So sánh phân số cùng mẫu.','Khi mẫu số bằng nhau, tử số lớn hơn biểu thị nhiều phần hơn, nếu các phần lấy từ cùng một đơn vị.','Tô các phần bằng nhau trên hai tờ giấy cùng cỡ.'),
('art-studio','Xưởng họa sĩ','creative','draw',0,'Diễn đạt ý tưởng bằng hình và màu.','Không chỉ có một bức vẽ đúng. Chọn màu, thử nét rồi kể điều mình muốn thể hiện.','Kể về một chi tiết con thích trong tranh.'),
('symmetry-studio','Gương đối xứng','creative','symmetry',1,'Khám phá hai nửa qua đường gấp.','Một nét ở bên trái có nét tương ứng cách đường gấp bằng khoảng ấy ở bên phải.','Gấp giấy, mở ra và vẽ hai cánh bướm.'),
('rhythm-orchestra','Dàn nhạc nhịp điệu','creative','rhythm',0,'Nghe và lặp lại một mẫu nhịp.','Nghe hết mẫu rồi vỗ lại. Có thể đếm chậm 1–2–3–4 để giữ nhịp.','Tạo nhịp bằng vỗ tay nhẹ; không mở âm thanh lớn.'),
('story-sequence','Đạo diễn chuyện nhỏ','creative','storyorder',1,'Sắp xếp mở đầu, diễn biến và kết thúc.','Một chuyện có việc xảy ra, cách nhân vật ứng xử và kết quả. Kể bằng lời của chính mình.','Kể ba câu về một việc hôm nay.'),
('observation-journal','Nhật ký khám phá','creative','journal',2,'Ghi điều quan sát được và câu hỏi mới.','Tách điều mắt thấy với điều mình đang đoán. Có thể vẽ thay cho viết và không ghi thông tin riêng.','Quan sát một chiếc lá trong ba ngày.'),
('design-bridge','Kỹ sư cây cầu','creative','bridge',3,'Thử thiết kế, quan sát rồi cải tiến.','Cầu cần bắc qua khoảng trống và chịu được tải. Chỉ dùng giấy, khối gỗ lớn và đồ chơi nhẹ, không leo lên mô hình.','Thử gấp một tờ giấy theo hai cách để làm cầu đồ chơi.'),
]
ACTIVITIES=[]
for row in ROWS:
 id,title,subject,kind,age,goal,lesson,home=row
 ACTIVITIES.append(dict(id=id,title=title,subject=subject,kind=kind,profiles=list(PROFILES)[age:],goal=goal,lesson=lesson,home=home,minutes=5 if age<2 else 8))

def illustrations():
 result={}
 for topic in ['animal','plant','environment','object']:
  data=json.loads((Path(__file__).parent/'resource'/f'topic-{topic}.json').read_text())
  for item in data['items']:
   result[item.get('slug',item['id'])]=item.get('image')
 return result
ART=illustrations()

def image(slug):
 return ART.get(slug) or next((v for k,v in ART.items() if k.startswith(slug+'-')),None)

def story(id,title,origin,value,art,pages,question,choices,answer=0,min_age=0):
 return dict(id=id,title=title,origin=origin,value=value,profiles=list(PROFILES)[min_age:],minutes=4,source='Bản kể ngắn do GoT biên soạn từ truyện dân gian/tác phẩm gốc đã thuộc phạm vi công cộng; không chép bản dịch hiện đại.',illustrations=[image(x) for x in art if image(x)],pages=[{'title':f'Chặng {i+1}','text':text} for i,text in enumerate(pages)],question=question,choices=choices,answer=answer)
# Only source-checked retellings enter the public story catalog.
STORIES=json.loads((Path(__file__).parent/'realm-stories.json').read_text())
