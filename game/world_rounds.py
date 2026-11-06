"""Age-aware practice generators; expected answers remain on the server."""
import random

def make_round(activity,profile):
 kind=activity['kind'];grade=['preschool','early-primary','middle-primary','upper-primary'].index(profile)
 limit=[5,20,100,1000][grade]
 task={'kind':'choice','prompt':activity['goal'],'hint':activity['lesson']}
 def choice(prompt,correct,others,visual=None):
  values=list(dict.fromkeys([str(correct)]+[str(x) for x in others if str(x)!=str(correct)]))[:[2,3,4,4][grade]]
  random.shuffle(values);task.update(prompt=prompt,options=[{'id':str(i),'label':label} for i,label in enumerate(values)])
  if visual:task['visual']=visual
  return str(values.index(str(correct)))
 def numeric(prompt,value,visual=None):
  return choice(prompt,value,[max(0,value-1),value+1,value+2],visual)
 def order(prompt,labels):
  items=[{'id':str(i),'label':s} for i,s in enumerate(labels)];random.shuffle(items)
  task.update(kind='order',prompt=prompt,items=items);return [str(i) for i in range(len(labels))]
 a=random.randint(1,max(2,limit//2));b=random.randint(1,max(2,limit//2))
 if kind=='count':
  n=random.randint(1,min(limit,20));answer=numeric('Có tất cả bao nhiêu quả?',n,{'type':'count','count':n,'symbol':'🍎'})
 elif kind=='compare':
  a=random.randint(1,min(limit,12));b=a+random.randint(1,3)
  left,right=random.sample([(a,'Giỏ A'),(b,'Giỏ B')],2)
  answer=choice('Giỏ nào có nhiều quả hơn?',left[1] if left[0]>right[0] else right[1],['Giỏ A','Giỏ B','Hai giỏ bằng nhau'],{'type':'baskets','left':left[0],'right':right[0]})
 elif kind=='add':answer=numeric(f'{a} + {b} = ?',a+b)
 elif kind=='subtract':a,b=max(a,b),min(a,b);answer=numeric(f'{a} − {b} = ?',a-b)
 elif kind=='multiply':a=random.randint(2,9);b=random.randint(2,9);answer=numeric(f'{a} hàng cây, mỗi hàng {b} cây. Có tất cả bao nhiêu cây?',a*b)
 elif kind=='divide':a=random.randint(2,9);b=random.randint(2,9);answer=numeric(f'Chia đều {a*b} chiếc bánh cho {a} bạn. Mỗi bạn được mấy chiếc?',b)
 elif kind=='fraction':
  d=random.choice([2,4,8]);n=random.randint(1,d-1);answer=choice(f'Hình có {d} phần bằng nhau, tô {n} phần. Phân số nào biểu thị phần tô?',f'{n}/{d}',[f'{d}/{n}',f'{n}/{d+1}',f'{n+1}/{d}'],{'type':'fraction','parts':d,'filled':n})
 elif kind=='clock':
  hour=random.randint(1,12);answer=choice('Đồng hồ chỉ mấy giờ?',f'{hour} giờ',[f'{hour%12+1} giờ',f'{(hour+2)%12+1} giờ'],{'type':'clock','hour':hour})
 elif kind=='money':
  cost=random.choice([4000,6000,8000,12000,14000,16000]);answer=choice(f'Mua quyển vở giá {cost:,} đồng, đưa 20.000 đồng. Được trả lại bao nhiêu?',f'{20000-cost:,} đồng',[f'{20000-cost+2000:,} đồng',f'{cost:,} đồng'])
 elif kind=='measure':
  n=random.randint(1,9);unit=random.choice(['m','kg']);factor=100 if unit=='m' else 1000;answer=numeric(f'{n} {unit} bằng bao nhiêu {"cm" if unit=="m" else "g"}?',n*factor)
 elif kind in ['numberline','numberpattern']:
  step=1 if kind=='numberline' else random.randint(2,9);start=random.randint(0,10);seq=[start+i*step for i in range(5)];answer=numeric(f'Điền số còn thiếu: {seq[0]}, {seq[1]}, ?, {seq[3]}, {seq[4]}',seq[2])
 elif kind=='wordmath':
  n=random.randint(3,12);each=random.randint(3,12);given=random.randint(1,n-1);answer=numeric(f'Có {n} hộp, mỗi hộp {each} bút. Đem tặng {given} hộp. Còn lại bao nhiêu chiếc bút?',(n-given)*each)
 elif kind=='vowel':
  target=random.choice(list('aăâeêioôơuưy'));answer=choice(f'Tìm chữ “{target.upper()}” giống chữ “{target}”.',target.upper(),random.sample(list('BCDGHKLMNPQRSTV'),3))
 elif kind=='tone':
  tone,label=random.choice([('hỏi','bả'),('ngã','bã'),('huyền','bà'),('sắc','bá'),('nặng','bạ')]);answer=choice(f'Từ nào có dấu {tone}?',label,['ba','bà','bá','bả','bã','bạ'])
 elif kind=='sentence':answer=order('Chọn các cụm từ theo thứ tự để tạo câu.',random.choice([['Chúng em','cùng nhau','trồng cây.'],['Buổi sáng,','chim nhỏ','hót trong vườn.'],['Bạn Lan','đọc sách','bên cửa sổ.']]))
 elif kind=='rhyme':
  word,correct,wrong=random.choice([('mèo','trèo',['mưa','hoa']),('bàn','đàn',['đèn','bút']),('hoa','loa',['lá','quả']),('sông','đồng',['suối','biển'])]);answer=choice(f'Từ nào có cùng vần với “{word}”?',correct,wrong)
 elif kind=='reading':
  passage,q,correct,wrong=random.choice([('Sáng nay, Mai đặt chậu đậu cạnh cửa sổ. Bạn tưới một ít nước rồi vẽ lại hai chiếc lá mới.','Mai nhìn thấy điều gì mới ở cây?','Hai chiếc lá',['Một bông hoa','Ba quả đậu']),('Nam mượn sách của An. Đọc xong, Nam đặt dấu trang sạch vào sách và trả lại bạn vào chiều thứ sáu.','Nam trả sách lúc nào?','Chiều thứ sáu',['Sáng thứ hai','Chiều chủ nhật']),('Sau cơn mưa, sân trường có vài vũng nước. Các bạn đi chậm theo lối khô và báo cô chỗ nền trơn.','Vì sao các bạn đi chậm?','Để tránh trượt ngã',['Để đến muộn','Vì không muốn vào lớp'])]);answer=choice(passage+'\n\n'+q,correct,wrong)
 elif kind=='punctuation':answer=choice('Chọn dấu kết thúc phù hợp: “Hôm nay bạn đọc sách gì…”','?',['.','! ', ','])
 elif kind=='synonym':
  word,right,wrong=random.choice([('chăm chỉ','siêng năng',['vội vàng','lười biếng']),('vui vẻ','hân hoan',['lo lắng','im lặng']),('to lớn','đồ sộ',['bé nhỏ','mảnh mai'])]);answer=choice(f'Từ nào gần nghĩa với “{word}”?',right,wrong)
 elif kind=='antonym':
  word,right,wrong=random.choice([('cao','thấp',['dài','rộng']),('nóng','lạnh',['ấm','nhiệt']),('nhanh','chậm',['sớm','vội']),('sạch','bẩn',['đẹp','sáng'])]);answer=choice(f'Từ nào trái nghĩa với “{word}”?',right,wrong)
 elif kind in ['growth','watercycle','routine','recipe','storyorder']:
  data={'growth':('Hạt phát triển theo thứ tự nào?',['Hạt được gieo','Hạt nảy mầm','Cây có lá','Cây trưởng thành']), 'watercycle':('Bắt đầu từ nước trong hồ, xếp hành trình của giọt nước.',['Nước bốc hơi','Hơi nước ngưng tụ','Mưa rơi','Nước tụ về sông hồ']), 'routine':('Xếp các bước rửa tay với xà phòng.',['Làm ướt tay','Xoa xà phòng và chà ít nhất 20 giây','Rửa sạch dưới nước','Lau khô tay']), 'recipe':('Chuẩn bị món bánh mì nguội cùng người lớn.',['Rửa tay','Chuẩn bị nguyên liệu sạch','Xếp phần nhân vào bánh','Dọn bàn và thưởng thức']), 'storyorder':('Xếp chuyện của hạt đậu theo trình tự.',['Bạn nhỏ gieo hạt','Mỗi ngày bạn chăm sóc','Một mầm xanh nhú lên','Bạn vẽ lại điều quan sát'])}
  prompt,labels=data[kind];answer=order(prompt,labels)
 elif kind=='habitat':
  animal,home,others=random.choice([('cá heo','Biển',['Tổ trên cây','Sa mạc']),('ếch','Ao và vùng ẩm',['Băng ở cực','Trong lò nóng']),('lạc đà một bướu','Sa mạc',['Đáy biển','Trong mây'])]);answer=choice(f'Môi trường nào phù hợp với {animal}?',home,others)
 elif kind=='classify':
  group,correct,others=random.choice([('động vật có vú','Cá heo',['Cá chép','Chim sẻ']),('vật liệu từ thực vật','Gỗ',['Thủy tinh','Thép']),('phương tiện đường sắt','Tàu hỏa',['Thuyền buồm','Xe đạp'])]);answer=choice(f'Chọn một thành viên thuộc nhóm {group}.',correct,others)
 elif kind=='weather':answer=choice('Trời nắng nóng. Chuẩn bị gì trước khi đi bộ cùng người lớn?','Mũ, nước uống và đường có bóng râm',['Áo khoác thật dày','Không cần mang nước'])
 elif kind=='space':
  prompt,right,others=random.choice([('Vật nào quay quanh Trái Đất?','Mặt Trăng',['Mặt Trời','Sao Hỏa']),('Vì sao có ngày và đêm?','Trái Đất tự quay',['Mặt Trời tắt vào ban đêm','Mặt Trăng che Trái Đất mỗi tối']),('Mặt Trời là gì?','Một ngôi sao',['Một hành tinh','Một vệ tinh của Trái Đất'])]);answer=choice(prompt,right,others)
 elif kind=='float':
  answer=choice('Cùng người lớn thả một miếng gỗ khô và viên sỏi đặc vào chậu nông. Dự đoán thường gặp nào hợp lý?','Gỗ thường nổi, sỏi thường chìm',['Cả hai luôn nổi','Vật nặng hơn luôn chìm trong mọi trường hợp']);task['hint']+=' Đây là dự đoán cho hai vật được mô tả, không phải quy tắc cho mọi loại gỗ hay mọi hình dạng.'
 elif kind=='senses':
  prompt,right,others=random.choice([('Để nghe tiếng chim, ta chủ yếu dùng gì?','Tai',['Mắt','Mũi']),('Để nhìn màu hoa, ta chủ yếu dùng gì?','Mắt',['Tai','Lưỡi']),('Để nhận mùi thức ăn quen thuộc từ khoảng cách an toàn, ta dùng gì?','Mũi',['Tai','Mắt'])]);answer=choice(prompt,right,others)
 elif kind in ['nutrition','emotion','kindness','roads','digital','recycle','help']:
  data={
  'nutrition':[('Bữa ăn nào đa dạng hơn?','Cơm, rau, đậu hoặc thịt/cá phù hợp và nước',['Chỉ ăn bánh ngọt','Chỉ uống nước thay mọi bữa'])],
  'emotion':[('Bạn buồn vì chưa ghép xong hình. Con có thể làm gì?','Nghỉ ngắn, hít thở và nhờ giúp ở bước khó',['Ném các mảnh ghép','Tự gọi mình là người kém cỏi']),('Khi bạn nói chưa muốn được ôm, con nên làm gì?','Tôn trọng và hỏi bạn cần hỗ trợ gì',['Ôm thật chặt cho bạn vui','Giận vì bạn từ chối'])],
  'kindness':[('Bạn làm rơi hộp bút. Hành động nào thể hiện sự quan tâm?','Hỏi bạn có cần giúp nhặt không',['Cười vì bạn vụng về','Giấu bút của bạn']),('Hai bạn muốn cùng một đồ chơi. Có thể thử cách nào?','Thỏa thuận thay lượt hoặc cùng chơi',['Giật lấy trước','Không cho ai chơi nữa'])],
  'roads':[('Muốn sang đường khi đi với người lớn, con nên làm gì?','Dừng lại, đi cùng người lớn và theo tín hiệu, quan sát',['Chạy theo bóng lăn ra đường','Đi qua bất kỳ chỗ nào có xe dừng'])],
  'digital':[('Người lạ trên mạng xin địa chỉ nhà. Con nên làm gì?','Không gửi và báo người lớn đáng tin',['Gửi để được nhận quà','Gửi cả mật khẩu']),('Video làm con sợ. Con có thể làm gì?','Dừng xem và nói với người lớn',['Cố xem hết để chứng tỏ mình giỏi','Giấu mọi người'])],
  'recycle':[('Tìm thấy pin đã dùng, con nên làm gì?','Nhờ người lớn đưa đến điểm thu gom phù hợp',['Mở pin xem bên trong','Bỏ pin vào bếp lửa']),('Cách nào giảm lãng phí nước?','Khóa vòi khi không sử dụng',['Để nước chảy suốt lúc đánh răng','Đổ nước uống còn sạch đi để lấy cốc mới'])],
  'help':[('Thấy dây điện bị hở, con nên làm gì?','Tránh xa, không chạm và báo người lớn',['Dùng tay kiểm tra','Lấy nước đổ lên']),('Bị lạc ở siêu thị, con nên làm gì?','Ở khu vực an toàn, nhờ nhân viên có nhận diện rõ giúp liên hệ gia đình',['Đi theo người lạ ra bãi xe','Tự đi xa để tìm đường về'])]}
  prompt,right,others=random.choice(data[kind]);answer=choice(prompt,right,others)
 elif kind=='pattern':
  seq=random.choice([['🔵','🟡'],['🌼','🍃','🍃'],['🔺','🔵','🟩']]);n=len(seq)*2;answer=choice('Hình tiếp theo là gì? '+' '.join((seq*3)[:n])+' …',seq[0],['🔵','🟡','🌼','🍃','🔺','🟩'])
 elif kind=='robot':
  task.update(kind='robot',prompt='Lập lệnh đưa robot đến cờ. Tránh ô đá; mỗi mũi tên đi một ô.',side=4,start=[0,0],goal=[3,3],walls=[[1,1],[2,1]])
  answer={'kind':'robot','goal':[3,3],'walls':[[1,1],[2,1]],'side':4}
 elif kind=='deduction':answer=choice('Có ba hộp: đỏ, xanh, vàng. Quả bóng không ở hộp đỏ và không ở hộp vàng. Bóng ở đâu?','Hộp xanh',['Hộp đỏ','Hộp vàng'])
 elif kind=='fractioncompare':
  den=random.choice([5,7,8,10]);x,y=random.sample(range(1,den),2);answer=choice(f'Cùng một chiếc bánh chia {den} phần bằng nhau. Phần nào lớn hơn?',f'{max(x,y)}/{den}',[f'{min(x,y)}/{den}','Hai phần bằng nhau'])
 elif kind in ['draw','symmetry','journal','bridge']:
  task.update(kind=kind,prompt={'draw':'Vẽ một khu vườn mà con muốn chăm sóc. Chọn nét và màu rồi thử kể về một chi tiết.','symmetry':'Vẽ ở bên trái đường giữa. Quan sát nét phản chiếu ở bên phải tạo thành đôi cánh.','journal':'Quan sát một vật quen thuộc. Ghi một điều con thấy và một điều con muốn hỏi. Không ghi tên, địa chỉ hay thông tin riêng.','bridge':'Thiết kế cầu trên lưới: chọn các ô làm mặt cầu nối bờ trái sang bờ phải. Sau đó thử cho xe đồ chơi qua mô hình.'}[kind]);answer={'kind':kind}
 elif kind=='rhythm':
  beats=[random.choice([0,1,2]) for _ in range(3+grade)];task.update(kind='rhythm',prompt='Nghe hoặc nhìn mẫu nhịp, rồi bấm lại các nút theo đúng thứ tự.',beats=beats);answer=beats
 elif kind=='ai_quiz':
  q=random.choice(activity['questions']);answer=choice(q['prompt'],q['choices'][q['answer']],[x for i,x in enumerate(q['choices']) if i!=q['answer']]);task['hint']=q['explanation']
 else:raise ValueError('Unsupported activity')
 return task,answer

def correct(expected,answer):
 if isinstance(expected,dict):
  kind=expected['kind']
  if kind=='robot':
   if not isinstance(answer,list) or not 1<=len(answer)<=30:return False
   x=y=0
   for command in answer:
    delta={'right':(1,0),'left':(-1,0),'up':(0,-1),'down':(0,1)}.get(command) if isinstance(command,str) else None
    if delta is None:return False
    x+=delta[0];y+=delta[1]
    if not 0<=x<expected['side'] or not 0<=y<expected['side'] or [x,y] in expected['walls']:return False
   return [x,y]==expected['goal']
  if kind in ('draw','symmetry'):return isinstance(answer,dict) and (answer.get('reflection') is True or type(answer.get('strokes')) is int and answer['strokes']>=3)
  if kind=='journal':return isinstance(answer,dict) and (answer.get('reflection') is True or type(answer.get('characters')) is int and 15<=answer['characters']<=1200)
  if kind=='bridge':
   if not isinstance(answer,list) or not 6<=len(answer)<=24 or any(type(v) is not int or not 0<=v<36 for v in answer):return False
   cells=set(answer);todo=[v for v in cells if v%6==0];seen=set(todo)
   while todo:
    v=todo.pop()
    if v%6==5:return True
    for w in cells-seen:
     if abs(w//6-v//6)+abs(w%6-v%6)==1:seen.add(w);todo.append(w)
   return False
 return type(answer) is type(expected) and answer==expected
