// Small helper JS: mobile nav toggle
document.addEventListener('DOMContentLoaded', function(){
  var btn = document.getElementById('nav-toggle');
  var links = document.querySelector('.nav-links');
  if(btn && links){
    btn.addEventListener('click', function(){
      if(links.style.display === 'flex' || links.style.display === ''){
        links.style.display = 'none';
      } else {
        links.style.display = 'flex';
      }
    });
    // close when clicking outside
    document.addEventListener('click', function(e){
      if(!btn.contains(e.target) && !links.contains(e.target) && window.innerWidth <= 900){
        links.style.display = 'none';
      }
    });
  }
  // notes hover preview
  var previewEl = null;
  function makePreview() {
    previewEl = document.createElement('div');
    previewEl.className = 'notes-popover';
    previewEl.style.position = 'absolute';
    previewEl.style.zIndex = 9999;
    previewEl.style.minWidth = '220px';
    previewEl.style.maxWidth = '360px';
    previewEl.style.background = '#fff';
    previewEl.style.border = '1px solid rgba(15,23,42,0.06)';
    previewEl.style.boxShadow = '0 10px 30px rgba(2,6,23,0.08)';
    previewEl.style.padding = '10px';
    previewEl.style.borderRadius = '8px';
    previewEl.style.display = 'none';
    document.body.appendChild(previewEl);
  }
  if(!previewEl) makePreview();
  document.querySelectorAll('.notes-preview').forEach(function(el){
    var tid = null;
    el.addEventListener('mouseenter', function(ev){
      var id = el.dataset.leadId;
      tid = setTimeout(function(){
        fetch('/lead/' + id + '/notes_json').then(function(r){return r.json()}).then(function(notes){
          if(!notes || notes.length===0){
            previewEl.innerHTML = '<em>No notes</em>';
          } else {
            previewEl.innerHTML = notes.map(function(n){return '<div style="margin-bottom:8px"><div style="font-size:0.85em;color:#6b7280">'+n.created_at+'</div><div style="white-space:pre-wrap">'+ (n.note) +'</div></div>'}).join('');
          }
          previewEl.style.display = 'block';
          var rect = el.getBoundingClientRect();
          previewEl.style.left = (rect.right + 10) + 'px';
          previewEl.style.top = (rect.top + window.scrollY) + 'px';
        })
      }, 200);
    });
    el.addEventListener('mouseleave', function(){
      clearTimeout(tid);
      previewEl.style.display = 'none';
    });
  });
});
