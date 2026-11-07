'use strict';
(() => {
 const host = document.querySelector('#realmFilms');
 const films = [
  ['environment', 'Một hạt mầm, một khu rừng', 'Chăm cây · Giữ nước sạch'],
  ['animals', 'Lắng nghe khu rừng', 'Quan sát · Tôn trọng động vật'],
  ['transport', 'Những chuyến đi an toàn', 'Phương tiện · Cùng người lớn sang đường']
 ];
 const dialog = document.createElement('dialog');
 dialog.className = 'world-dialog realm-cinema';
 dialog.setAttribute('aria-label', 'Rạp phim của Mây');
 const title = document.createElement('h2');
 const video = document.createElement('video');
 const close = document.createElement('button');
 const note = document.createElement('p');
 video.controls = true;
 video.playsInline = true;
 video.preload = 'none';
 video.style.width = '100%';
 video.setAttribute('controlslist', 'nodownload noremoteplayback');
 close.textContent = 'Bỏ qua / Đóng phim · Quay lại thế giới';
 close.className = 'world-button';
 close.onclick = () => dialog.close();
 note.textContent = 'Phim hoạt cảnh 2D do GoT tạo · 8 giây. Mình cùng kể lại một điều vừa nhìn thấy nhé.';
 dialog.append(title, video, note, close);
 document.body.append(dialog);
 function openFilm(id, label, preview = false) {
  if (!preview && !document.dispatchEvent(new Event('realm:play-request', {cancelable: true}))) return;
  document.dispatchEvent(new Event('realm:cinema-open'));
  title.textContent = label;
  video.src = '/world-assets/film-' + id;
  dialog.showModal();
  video.focus();
 }
 document.addEventListener('realm:expired', () => dialog.close());
 window.addEventListener('pagehide', () => video.pause());
 dialog.addEventListener('close', () => {
  document.dispatchEvent(new Event('realm:cinema-close'));
  video.pause();
  video.removeAttribute('src');
  video.load();
 });
 document.addEventListener('visibilitychange', () => { if (document.hidden) video.pause(); });
 for (const [id, label, description] of films) {
  const button = document.createElement('button');
  button.className = 'realm-film';
  const image = new Image();
  image.src = '/world-assets/' + id;
  image.alt = '';
  image.loading = 'lazy';
  const heading = document.createElement('b');
  heading.textContent = '▷ ' + label;
  const subtitle = document.createElement('small');
  subtitle.textContent = description + ' · 8 giây';
  button.append(image, heading, subtitle);
  button.onclick = () => openFilm(id, label);
  host.append(button);
 }
 document.querySelector('#realmWelcome').onclick = () => openFilm('opening', 'Cùng Mây bước vào Miền Diệu Kỳ', true);
})();
