(() => {
  const csrf = document.currentScript.dataset.csrf;
  const topic = document.querySelector('#topic'), items = document.querySelector('#items');
  const notice = document.querySelector('#notice'), editor = document.querySelector('#editor');
  const form = document.querySelector('#edit-form');
  let current = [];
  async function api(path, options = {}) {
    const response = await fetch(path, {...options, cache:'no-store', headers:{'X-CSRF-Token':csrf,...options.headers}});
    let result;
    try { result = await response.json(); } catch { throw new Error('Không thể đọc phản hồi từ máy chủ.'); }
    if (!response.ok) throw new Error(result.message || 'Không thể cập nhật Drive. Hãy kiểm tra quyền truy cập.');
    return result;
  }
  const base = () => '/api/admin/resources/' + encodeURIComponent(topic.value);
  async function load() {
    items.replaceChildren();
    if (!topic.value) return;
    notice.textContent = 'Đang đọc tài nguyên từ Drive…';
    try {
      current = (await api(base())).items || [];
      for (const item of current) {
        const card = document.createElement('article');
        const image = document.createElement('img');
        image.src = '/thumb/' + item.image; image.alt = item.viName; image.loading = 'lazy';
        image.style.cssText = 'width:100%;height:150px;object-fit:contain';
        const title = document.createElement('h3'); title.textContent = item.viName;
        const edit = document.createElement('button'); edit.textContent = 'Sửa'; edit.onclick = () => open(item);
        const remove = document.createElement('button'); remove.textContent = 'Xóa';
        remove.onclick = async () => {
          if (!confirm('Xóa “' + item.viName + '” khỏi chủ đề và chuyển ảnh không còn dùng vào thùng rác Drive?')) return;
          remove.disabled = true;
          try { await api(base() + '/' + encodeURIComponent(item.id), {method:'DELETE'}); await load(); }
          catch (error) { notice.textContent = error.message; remove.disabled = false; }
        };
        card.append(image, title, edit, remove); items.append(card);
      }
      notice.textContent = current.length + ' tài nguyên trên Drive.';
    } catch (error) { notice.textContent = error.message; }
  }
  function open(item = {}) {
    if (!topic.value) { notice.textContent = 'Chọn chủ đề trước.'; return; }
    form.reset();
    for (const field of ['id','viName','enName','description','descriptionEn']) form.elements[field].value = item[field] || '';
    form.elements.image.required = !item.id;
    document.querySelector('#editor-title').textContent = item.id ? 'Sửa tài nguyên' : 'Thêm tài nguyên';
    document.querySelector('#edit-error').textContent = ''; editor.showModal();
  }
  form.onsubmit = async event => {
    event.preventDefault();
    const button = form.querySelector('[type=submit]'); button.disabled = true;
    try {
      const data = new FormData(form), id = data.get('id'); data.delete('id');
      await api(base() + (id ? '/' + encodeURIComponent(id) : ''), {method:'POST',body:data});
      editor.close(); await load();
    } catch (error) { document.querySelector('#edit-error').textContent = error.message; }
    finally { button.disabled = false; }
  };
  document.querySelector('#cancel-edit').onclick = () => editor.close();
  document.querySelector('#add').onclick = () => open(); topic.onchange = load;
  async function migrationStatus() {
    try {
      const status = await api('/api/admin/drive/migration');
      const labels = {'verify-archive':'Đang kiểm tra gói ảnh','upload-images':'Đang chuyển ảnh vào Drive','complete':'Đã hoàn tất chuyển dữ liệu','failed':'Chuyển dữ liệu chưa hoàn tất'};
      notice.textContent = (labels[status.stage] || 'Đang chuẩn bị') + (status.total ? ': ' + status.done + '/' + status.total : '') + (status.message ? '. ' + status.message : '');
      document.querySelector('#migrate').disabled = status.running;
      if (status.running) setTimeout(migrationStatus,3000);
    } catch (error) { notice.textContent = error.message; document.querySelector('#migrate').disabled = false; }
  }
  document.querySelector('#migrate').onclick = async () => {
    document.querySelector('#migrate').disabled = true;
    try { await api('/api/admin/drive/migration',{method:'POST'}); await migrationStatus(); }
    catch (error) { notice.textContent = error.message; document.querySelector('#migrate').disabled = false; }
  };
  api('/api/admin/topics').then(data => {
    for (const entry of data.topics) { const option=document.createElement('option'); option.value=entry.id; option.textContent=entry.name.vi; topic.append(option); }
  }).catch(error => { notice.textContent=error.message; });
  migrationStatus();
})();
