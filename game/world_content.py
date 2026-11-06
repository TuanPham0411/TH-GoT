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
STORIES=[
 story('cay-khe','Cây khế','Việt Nam','Biết đủ và chia sẻ',['cay-khe','chim-phuong-hoang'],[
 'Người em chăm chỉ sống bên cây khế nhỏ. Mỗi ngày, em tưới nước, nhổ cỏ và chờ quả chín. Khi một con chim lớn đến ăn khế, em buồn nói: “Khế là nguồn sống của nhà tôi, bạn hãy để lại cho chúng tôi một ít.”',
 'Chim hứa đưa em đến đảo có vàng để cảm ơn. Em khâu một chiếc túi nhỏ như lời chim dặn. Trên đảo, em chỉ lấy vừa đủ, cẩn thận buộc túi rồi trở về. Có cuộc sống tốt hơn, em vẫn chăm vườn và giúp những người khó khăn.',
 'Người anh nghe chuyện liền đổi nhà cửa lấy cây khế. Khi chim đến, anh chuẩn bị chiếc túi thật to và chất quá nhiều vàng. Đường về trở nên nặng nề. Nhận ra nguy hiểm, anh phải bỏ bớt vàng để chim có thể đưa mình trở lại.',
 'Về nhà, người anh hiểu rằng lòng tham đã khiến chuyến đi mất an toàn. Người em mời anh cùng trồng cây và làm việc. Câu chuyện gợi một câu hỏi: chúng ta cần bao nhiêu là đủ, và có thể chia sẻ điều gì với người khác?'],
 'Vì sao chiếc túi nhỏ lại là lựa chọn tốt?',['Vừa đủ nhu cầu và giúp chuyến đi an toàn','Vì người em không biết đếm','Vì vàng không có ích']),
 story('thach-sanh','Thạch Sanh','Việt Nam','Lòng tốt đi cùng sự thật',['cay-da','environment-forest-v83'],[
 'Thạch Sanh sống giản dị dưới gốc đa, làm việc chăm chỉ và sẵn lòng giúp người khác. Lý Thông thấy chàng khỏe mạnh thì tìm cách lợi dụng. Khi được nhờ một việc khó, Thạch Sanh nhận lời vì nghĩ mình đang giúp bạn.',
 'Sau nhiều thử thách, Thạch Sanh cứu được những người gặp nạn nhưng công lao lại bị Lý Thông nhận lấy. Chàng buồn, song không vì thế mà làm điều xấu. Thạch Sanh tìm cách nói rõ sự thật và chờ một cơ hội được lắng nghe.',
 'Tiếng đàn của Thạch Sanh vang lên, giúp mọi người hiểu những điều đã xảy ra. Nhà vua nghe cả hai phía, tìm bằng chứng rồi trả lại công bằng cho chàng. Sự thật cần được nói bằng lời rõ ràng, chứ không phải bằng cách làm tổn thương nhau.',
 'Trong ngày sum họp, niêu cơm nhỏ của Thạch Sanh cứ đầy mãi để mời mọi người. Chàng chọn chia sẻ thay vì trả đũa. Lòng tốt rất đáng quý; đồng thời, khi bị lợi dụng, ta có thể kể chuyện với người lớn đáng tin để được bảo vệ.'],
 'Khi bị người khác nhận công của mình, con nên làm gì?',['Bình tĩnh nói sự thật và tìm người lớn giúp','Im lặng vì mình không được nói','Trả đũa để bạn buồn hơn'],min_age=1),
 story('thanh-giong','Thánh Gióng','Việt Nam','Chung sức vì cộng đồng',['cay-tre','environment-river-v83'],[
 'Ở một làng quê, cậu bé Gióng lớn lên trong sự chăm sóc của mẹ. Khi làng cần người bảo vệ, Gióng cất tiếng nhận việc. Mẹ ngạc nhiên nhưng lắng nghe điều con muốn làm và nhờ bà con cùng chuẩn bị.',
 'Gióng lớn nhanh, cần rất nhiều cơm áo. Người mang gạo, người may áo, người góp sức làm ngựa sắt. Mỗi gia đình góp một chút theo khả năng. Việc lớn dần trở thành công việc của cả làng, không phải của riêng một người.',
 'Trong truyền thuyết, Gióng cưỡi ngựa sắt bảo vệ quê hương. Khi cần, chàng dùng cả những bụi tre bên đường. Những chi tiết kỳ diệu làm nổi bật ước mơ về sức mạnh và lòng đoàn kết của người xưa.',
 'Khi quê hương bình yên, Gióng để lại dấu chân trong lời kể của dân làng. Chúng ta không cần làm việc lớn như trong truyền thuyết mới giúp được cộng đồng. Giữ sân chơi sạch, quan tâm bạn và làm phần việc vừa sức cũng có ý nghĩa.'],
 'Điều gì giúp Gióng có sức mạnh trong câu chuyện?',['Sự chung sức của mẹ và dân làng','Chỉ riêng bộ áo mới','Không cần ai giúp'],min_age=1),
 story('so-dua','Sọ Dừa','Việt Nam','Tôn trọng sự khác biệt',['cay-tre','con-bo'],[
 'Sọ Dừa có dáng vẻ khác những đứa trẻ trong làng. Nhiều người chỉ nhìn bề ngoài rồi cho rằng cậu không làm được việc gì. Nhưng mẹ lắng nghe mong muốn của con và giúp cậu tìm việc phù hợp.',
 'Sọ Dừa nhận chăm đàn bò. Cậu quan sát con đường, ghi nhớ chỗ có cỏ và đưa đàn về đúng giờ. Khi cần giúp đỡ, cậu biết nhờ người khác. Cô út nhìn thấy sự chăm chỉ ấy nên trò chuyện và đối xử với cậu bằng sự tôn trọng.',
 'Trong thế giới cổ tích, Sọ Dừa còn có nhiều khả năng kỳ diệu. Dù vậy, điều khiến người khác quý cậu không chỉ là phép màu mà là lòng tử tế và việc giữ lời. Một người không cần giống số đông mới xứng đáng được lắng nghe.',
 'Sọ Dừa và cô út tìm được cuộc sống vui vẻ, cùng học và giúp gia đình. Bản kể này mời chúng ta bỏ qua những lời chê bai ngoại hình. Hãy hỏi bạn muốn tham gia thế nào, rồi tạo cơ hội để mỗi người thể hiện khả năng.'],
 'Ta nên dựa vào điều gì để hiểu một người?',['Lắng nghe và tìm hiểu hành động, khả năng của họ','Chỉ nhìn dáng vẻ','Nghe lời trêu chọc của người khác']),
 story('ba-co-gai','Ba cô gái','Việt Nam','Quan tâm bằng hành động',['environment-forest-v83','cay-cuc-trang'],[
 'Một người mẹ nuôi ba cô con gái khôn lớn. Khi các con có gia đình riêng, mẹ vẫn nhớ từng người. Một hôm mẹ bị mệt, nhờ bạn Sóc mang lời nhắn: “Các con về thăm mẹ khi có thể nhé.”',
 'Hai cô chị nghe tin nhưng mải tính những việc đang làm. Cô út dừng lại, hỏi rõ mẹ cần gì, nhờ người nhà hỗ trợ việc còn lại rồi chuẩn bị về thăm. Cô không đi một mình khi chưa biết đường, mà tìm cách về cho an toàn.',
 'Về đến nhà, cô út lấy nước, chuẩn bị đồ ăn và mời người có chuyên môn chăm sóc mẹ. Cô cũng báo cho các chị để mọi người cùng chia việc. Quan tâm không có nghĩa phải tự mình làm hết hoặc biết mọi cách chữa bệnh.',
 'Các chị hiểu ra và thu xếp đến với mẹ. Trong bản kể nhẹ nhàng này, cả nhà cùng sửa điều chưa tốt thay vì nhận một hình phạt đáng sợ. Một cuộc gọi, một lời hỏi han và một việc giúp vừa sức đều có thể thể hiện tình yêu thương.'],
 'Cách giúp người thân đang mệt nào phù hợp?',['Hỏi nhu cầu và nhờ người lớn hỗ trợ chăm sóc','Tự lấy thuốc bất kỳ cho uống','Cho rằng phải tự làm mọi việc']),
 story('tri-khon','Trí khôn của ta đây','Việt Nam','Bình tĩnh tìm cách giải quyết',['ho-dong-duong','trau-nuoc'],[
 'Một con hổ tò mò nhìn người nông dân và con trâu làm việc. Hổ rất khỏe nên ngạc nhiên vì sao con trâu lại biết đi theo những hiệu lệnh nhỏ. Nó hỏi người nông dân: “Điều gì giúp bác làm được như vậy?”',
 'Người nông dân nói về trí khôn: quan sát, ghi nhớ và nghĩ cách làm. Hổ tưởng trí khôn là một món đồ có thể cầm được nên xin xem. Người nông dân hiểu rằng cần một cách giải thích khiến hổ suy nghĩ chứ không chỉ nghe lời.',
 'Trong truyện dân gian có nhiều chi tiết phóng đại về cuộc gặp này. Bản kể của chúng ta dừng ở một thử thách: đưa nước qua rãnh bằng chiếc máng. Người nông dân đo chỗ đặt, chống máng chắc rồi để nước tự chảy. Hổ thấy sức mạnh không phải cách giải quyết duy nhất.',
 'Trí khôn không phải bí mật để hơn thua; đó là khả năng học hỏi và tìm phương án. Với việc nguy hiểm, trẻ cần lùi lại và nhờ người lớn, không thử bắt chước người nông dân đến gần thú dữ. Cùng nghĩ một cách an toàn cũng là dùng trí khôn.'],
 'Trí khôn có thể thể hiện ở việc nào?',['Quan sát, suy nghĩ và chọn cách an toàn','Luôn dùng sức mạnh','Đến gần thú dữ để thử sức'],min_age=1),
 story('hoa-cuc','Sự tích hoa cúc trắng','Việt Nam','Yêu thương và hy vọng',['cay-cuc-la-ma'],[
 'Một cô bé sống cùng mẹ trong ngôi nhà nhỏ. Khi mẹ bị ốm, cô bé lo lắng và tìm người lớn giúp chăm sóc. Trong lúc chờ, em muốn làm một điều để mẹ vui hơn nên ra vườn tìm một bông hoa.',
 'Cô bé nhìn thấy bông cúc trắng đang nở. Theo lời kể dân gian, em gửi vào từng cánh hoa một ước mong mẹ được ở bên mình thật lâu. Em nâng niu bông hoa, nghĩ đến những ngày hai mẹ con đã chăm sóc khu vườn.',
 'Những cánh nhỏ xếp thành nhiều lớp, như rất nhiều lời chúc bình an. Em mang hoa về, ngồi bên mẹ và kể điều vừa thấy. Người lớn vẫn tiếp tục chăm sóc và đưa mẹ đến người có chuyên môn khi cần.',
 'Hoa cúc trong câu chuyện là biểu tượng của tình yêu thương và hy vọng, không phải thuốc chữa bệnh hay chiếc đồng hồ đếm ngày sống. Khi lo cho người thân, con có thể nói ra cảm xúc và nhờ người lớn cùng tìm cách giúp.'],
 'Bông hoa trong bản kể tượng trưng cho điều gì?',['Tình yêu thương và hy vọng','Một loại thuốc thay thế bác sĩ','Lỗi của cô bé khi mẹ bị ốm']),
 story('qua-bau','Quả bầu tiên','Việt Nam','Chăm sóc không đòi phần thưởng',['cay-bau','chim-en'],[
 'Cậu bé nhìn thấy một chú chim én gặp khó khăn gần nhà. Cậu gọi người lớn đến xem rồi cùng chuẩn bị một góc yên tĩnh, không tự giữ chim hoang làm đồ chơi. Khi chim khỏe và có thể bay, cậu vui vẻ để chim trở lại bầu trời.',
 'Mùa sau, trong câu chuyện cổ tích, chim én mang đến một hạt bầu. Cậu bé gieo hạt, làm giàn và chăm cây mỗi ngày. Cây không lớn ngay lập tức; cậu phải chờ, quan sát lá và nhờ người lớn giúp khi giàn nghiêng.',
 'Quả bầu lớn lên, mang trong nó một món quà kỳ diệu. Cậu bé vui nhưng vẫn nhớ vì sao mình đã giúp chim: vì chú chim cần được chăm sóc. Cậu chia sẻ niềm vui và thành quả với gia đình, hàng xóm.',
 'Có người muốn bắt chước chỉ để nhận quà. Nhưng lòng tốt không phải cuộc đổi chác chắc chắn có phần thưởng. Với động vật gặp nạn ngoài đời, hãy quan sát từ xa và nhờ người lớn hoặc nơi cứu hộ phù hợp giúp đỡ.'],
 'Vì sao cậu bé giúp chú chim?',['Vì nhận ra chú chim cần được giúp','Vì chắc chắn sẽ nhận vàng','Để giữ chim trong nhà']),
 story('rua-tho','Rùa và Thỏ','Thế giới · ngụ ngôn Aesop','Kiên trì và tôn trọng bạn',['rua-can-khong-lo','tho-chau-au'],[
 'Thỏ chạy nhanh và rất tự tin. Khi thấy Rùa bước chậm, Thỏ trêu bạn. Rùa không muốn cãi nhau nên đề nghị một cuộc thi nhỏ với đường đi an toàn đã được các bạn thống nhất. Cả hai cùng biết vị trí xuất phát và đích đến.',
 'Thỏ lao đi rất nhanh. Nhìn lại không thấy Rùa ở gần, Thỏ quyết định nghỉ dưới bóng cây rồi ngủ quên. Rùa thì đi theo nhịp của mình, thỉnh thoảng dừng ngắn để thở và xem mình còn đi đúng đường không.',
 'Từng bước nhỏ đưa Rùa đến gần đích. Khi Thỏ tỉnh giấc và chạy tiếp, Rùa đã hoàn thành đường đi. Thỏ ngạc nhiên nhận ra rằng nhanh ở một đoạn không có nghĩa chắc chắn hoàn thành cả công việc.',
 'Rùa không chế giễu Thỏ. Hai bạn nói lời chúc mừng và xin lỗi nhau. Có việc cần nhanh, có việc cần chậm để cẩn thận; điều quan trọng là biết mục tiêu, luyện tập và không coi thường khả năng của người khác.'],
 'Điều gì giúp Rùa hoàn thành cuộc thi?',['Đi đều, theo kế hoạch và không bỏ cuộc','Chế giễu Thỏ','Giấu đường đến đích']),
 story('su-tu-chuot','Sư tử và Chuột','Thế giới · ngụ ngôn Aesop','Ai cũng có thể giúp đỡ',['su-tu-chau-phi','chuot-nha'],[
 'Chuột nhỏ chạy qua chỗ Sư tử đang nghỉ và vô tình làm bạn tỉnh giấc. Chuột xin lỗi. Sư tử nghe lời giải thích, để Chuột rời đi và nhắc bạn quan sát đường chạy cho cẩn thận.',
 'Chuột hứa sẽ giúp lại khi có dịp. Sư tử nghĩ mình to khỏe nên khó có lúc cần đến một người bạn bé xíu. Nhưng Sư tử không biết rằng mỗi loài có những khả năng rất khác nhau.',
 'Một ngày, Sư tử vướng vào tấm lưới cũ trong rừng. Chuột nghe tiếng gọi, nhìn rõ chỗ có thể giúp rồi gặm từng sợi dây. Nhờ những chiếc răng nhỏ và sự kiên nhẫn, Chuột tạo được khoảng hở để Sư tử ra ngoài.',
 'Sư tử cảm ơn và hiểu rằng kích thước không quyết định giá trị của một người bạn. Đây là chuyện ngụ ngôn; ngoài đời, trẻ không đến gần thú lớn hay tự gỡ bẫy. Nếu thấy động vật mắc kẹt, hãy nhờ người lớn và người cứu hộ.'],
 'Sư tử học được điều gì?',['Bạn nhỏ cũng có khả năng đáng quý','Chỉ người khỏe mới giúp được người khác','Không cần cảm ơn bạn']),
 story('kien-bo-cau','Kiến và Bồ câu','Thế giới · ngụ ngôn Aesop','Để ý nhu cầu của người khác',['kien-den','chim-bo-cau'],[
 'Kiến tìm nước uống bên dòng suối và trượt xuống mép nước. Bồ câu ở trên cành nghe tiếng động. Nó quan sát, thấy một chiếc lá gần bờ rồi thả lá xuống chỗ Kiến có thể bám vào.',
 'Kiến lên được chiếc lá và trôi tới bờ cạn. Nó nghỉ một lúc, cảm ơn Bồ câu. Bạn không hỏi Kiến có món quà nào trả lại; thấy bạn nhỏ an toàn đã là điều đáng vui.',
 'Sau đó, Kiến nhìn thấy một người đang tiến đến gần chỗ Bồ câu nghỉ. Nó tạo ra tiếng động nhỏ báo cho Bồ câu chú ý. Bồ câu nhận ra tình huống và bay tới một chỗ yên tĩnh hơn.',
 'Hai bạn hiểu rằng quan tâm bắt đầu từ việc để ý và hành động phù hợp khả năng. Với trẻ em, cứu người hay vật ở dưới nước là việc của người lớn được huấn luyện: hãy gọi giúp đỡ, không tự nhảy xuống nước.'],
 'Nếu thấy người gặp nguy hiểm dưới nước, trẻ nên làm gì?',['Gọi người lớn hoặc người cứu hộ, không tự nhảy xuống','Lập tức nhảy xuống dù chưa biết bơi','Bỏ đi mà không báo ai']),
 story('cu-cai','Củ cải khổng lồ','Thế giới · truyện dân gian Nga','Hợp tác và phân công',['cay-cu-cai','cho-nha','meo-nha'],[
 'Ông trồng một cây cải trong vườn. Mỗi ngày ông tưới vừa đủ và nhổ cỏ. Đến mùa thu hoạch, củ cải đã lớn khác thường. Ông kéo thử một mình, nhưng củ cải vẫn nằm yên trong đất.',
 'Ông gọi bà giúp. Bà gọi cháu, rồi cả nhà nhờ thêm những người bạn. Mọi người đứng chắc chân, thống nhất lúc cùng kéo và để ý không làm bạn phía sau bị ngã. Củ cải vẫn chưa chịu nhúc nhích.',
 'Bạn Chuột nhỏ đến góp sức. Cả nhóm đổi cách đứng, đếm “một, hai, ba” rồi cùng làm. Lần này củ cải bật lên. Không ai nói mình là người duy nhất kéo được; thành quả thuộc về nỗ lực của cả nhóm.',
 'Cả nhà cùng chuẩn bị món ăn từ củ cải, mỗi người nhận một phần việc vừa sức. Hợp tác không chỉ là có thêm nhiều người mà còn là biết nghe, phân công và phối hợp. Bạn nhỏ nhất cũng cần được mời tham gia và cảm ơn.'],
 'Vì sao cả nhóm kéo được củ cải?',['Cùng phối hợp và góp phần theo khả năng','Vì chỉ một người có ích','Vì người nhỏ nhất phải làm hết']),
 story('vit-con','Chú vịt con khác biệt','Thế giới · H. C. Andersen, 1843','Tôn trọng bản thân và bạn bè',['vit-nha','thien-nga-trang'],[
 'Một chú chim non nở trong đàn vịt nhưng trông khác các bạn. Vài lời trêu chọc khiến chú buồn và nghĩ mình không thuộc về đâu. Chú cần một nơi an toàn và những người chịu lắng nghe, chứ không cần cố giống mọi người.',
 'Qua những mùa trong năm, chú học cách tìm thức ăn và nhận biết nơi trú phù hợp. Có những ngày khó khăn, chú được các bạn tử tế giúp đỡ. Khi buồn, chú dần biết tìm sự hỗ trợ thay vì giữ mọi cảm xúc một mình.',
 'Mùa xuân tới, chú gặp một đàn thiên nga và nhận ra mình cũng thuộc loài ấy. Hình dáng mới giúp chú hiểu câu chuyện về bản thân. Nhưng giá trị của chú đã có từ trước, không cần đợi trở nên đẹp trong mắt người khác.',
 'Chú nhớ những ai đã đối xử tử tế khi mình còn nhỏ. Câu chuyện mời chúng ta bỏ cách gọi bạn bằng lời chê ngoại hình. Mỗi người phát triển theo nhịp riêng; được tôn trọng là quyền của mọi người, không phải phần thưởng cho vẻ đẹp.'],
 'Khi một bạn bị trêu vì khác biệt, con có thể làm gì?',['Ở bên bạn và nhờ người lớn giúp dừng việc trêu chọc','Cười theo để mình không bị trêu','Bảo bạn phải thay đổi mới đáng được chơi cùng']),
 story('ba-chu-heo','Ba chú heo con','Thế giới · truyện dân gian Anh','Chuẩn bị và giúp đỡ nhau',['lon-nha','soi-xam'],[
 'Ba anh em Heo muốn dựng những ngôi nhà nhỏ. Bạn thứ nhất chọn rơm, bạn thứ hai chọn cành cây, bạn thứ ba chọn vật liệu chắc hơn và dành thời gian tìm cách xây. Mỗi bạn đều hào hứng với ý tưởng của mình.',
 'Một cơn gió mạnh làm hai căn nhà nhẹ rung lắc. Trong chuyện cổ tích, Sói còn đến thử thổi cửa. Hai bạn Heo nhận ra công trình chưa vững nên rời chỗ không an toàn và đến nhà người anh em thứ ba.',
 'Ngôi nhà chắc giúp cả ba có chỗ trú. Bạn thứ ba không trách móc mà mời hai bạn vào, đóng cửa và gọi người lớn hỗ trợ. Không ai cần đối đầu với Sói hay dùng bếp lửa để giải quyết tình huống.',
 'Khi trời yên, ba bạn cùng sửa thiết kế, thử độ vững của mô hình và phân chia công việc. Chuẩn bị cẩn thận không có nghĩa không bao giờ sai; quan trọng là nhận ra vấn đề, tìm chỗ an toàn và cùng cải tiến.'],
 'Khi thấy nhà hoặc mô hình có nguy cơ đổ, con nên làm gì?',['Rời chỗ nguy hiểm và báo người lớn','Đứng bên dưới để đỡ','Thử trèo lên xem chắc chưa']),
 story('khan-do','Cô bé quàng khăn đỏ','Thế giới · truyện dân gian châu Âu','Hỏi người lớn trước khi đổi kế hoạch',['soi-xam','environment-forest-v83'],[
 'Khăn Đỏ cùng mẹ chuẩn bị giỏ đồ thăm bà. Hai mẹ con nói rõ con đường và người sẽ đi cùng. Khi ra ngoài, Khăn Đỏ biết mình có thể hỏi lại nếu chưa nhớ, và không tự đổi lộ trình mà không báo.',
 'Trên đường, một người lạ gợi ý đi theo lối khác để hái hoa. Khăn Đỏ thích hoa nhưng nhớ rằng lời mời hấp dẫn vẫn cần được kiểm tra. Cô dừng ở chỗ có người quen và nhờ người lớn liên lạc với mẹ.',
 'Trong phiên bản kể an toàn này, người lớn nhận ra lời chỉ đường không đáng tin, giúp Khăn Đỏ tiếp tục theo kế hoạch. Cô đến thăm bà cùng người đã được gia đình thống nhất. Giỏ đồ và câu chuyện làm bà rất vui.',
 'Khăn Đỏ học rằng khi không chắc, em có quyền nói “Cháu cần hỏi người nhà trước”. Nếu một bạn nhỏ bị lừa, đó không phải lý do để trách hay làm bạn xấu hổ; điều cần làm là giúp bạn tìm lại sự an toàn.'],
 'Con có thể nói gì trước lời mời đi theo người chưa được gia đình đồng ý?',['Cháu cần hỏi người nhà trước','Cháu sẽ đi mà không báo ai','Cháu phải nhận lời để không bất lịch sự']),
 story('hoang-de','Bộ quần áo của hoàng đế','Thế giới · H. C. Andersen, 1837','Dám hỏi và nói điều mình quan sát',['environment-forest-v83'],[
 'Một hoàng đế rất thích được khen. Hai người thợ tự nhận làm được loại vải đặc biệt, rồi nói rằng ai không nhìn thấy vải thì không thông minh. Mọi người lo bị đánh giá nên không ai dám hỏi rõ.',
 'Các quan đến xem nhưng chỉ thấy khung dệt trống. Vì sợ bị chê, họ vẫn gật đầu khen. Một lời chưa được kiểm chứng dần trở thành điều ai cũng lặp lại, dù không ai có bằng chứng.',
 'Đến ngày giới thiệu trang phục, một em nhỏ nói điều mình quan sát được: “Cháu chưa thấy tấm vải ấy”. Em không nhằm làm ai xấu hổ mà chỉ hỏi thật. Lúc đó mọi người mới nhận ra mình cũng cần được phép thắc mắc.',
 'Bản kể này khép lại khi hoàng đế dừng buổi giới thiệu để kiểm tra và thay sang bộ áo quen thuộc. Biết nhận sai giúp ta học được điều mới. Không nhìn thấy hay chưa hiểu điều gì không có nghĩa mình kém thông minh.'],
 'Khi chưa thấy bằng chứng, con có thể làm gì?',['Hỏi lại và kiểm tra điều mình quan sát','Khen theo để khỏi khác mọi người','Chê người đặt câu hỏi'],min_age=2),
]
