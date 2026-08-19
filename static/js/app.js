document.addEventListener('DOMContentLoaded', function () {
  var mobileMenu = document.getElementById('mobileMenu');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebarOverlay');

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
  }

  if (mobileMenu && sidebar && overlay) {
    mobileMenu.addEventListener('click', function () {
      sidebar.classList.add('open');
      overlay.classList.add('show');
    });
    overlay.addEventListener('click', closeSidebar);
    document.querySelectorAll('.nav-item').forEach(function (item) {
      item.addEventListener('click', function () {
        if (window.innerWidth <= 900) closeSidebar();
      });
    });
  }

  var searchInput = document.getElementById('searchInput');
  var statusFilter = document.getElementById('statusFilter');
  var table = document.getElementById('leadsTable');
  function filterLeads() {
    if (!table) return;
    var search = (searchInput ? searchInput.value : '').toLowerCase().trim();
    var status = (statusFilter ? statusFilter.value : '').toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function (row) {
      var text = row.innerText.toLowerCase();
      row.style.display = (!search || text.indexOf(search) !== -1) && (!status || text.indexOf(status) !== -1) ? '' : 'none';
    });
  }
  if (searchInput) searchInput.addEventListener('input', filterLeads);
  if (statusFilter) statusFilter.addEventListener('change', filterLeads);

  document.querySelectorAll('[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});