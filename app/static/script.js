
// Toggle action menu for 3-dots button
function toggleMenu(btn) {
  // close other menus
  document.querySelectorAll('.action-menu').forEach(m => {
    if (m !== btn.nextElementSibling) m.style.display = 'none';
  });

  const menu = btn.nextElementSibling;
  if (!menu) return;
  menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';

  // click outside to close
  setTimeout(() => {
    window.addEventListener('click', function onDocClick(e) {
      if (!menu.contains(e.target) && e.target !== btn) {
        menu.style.display = 'none';
        window.removeEventListener('click', onDocClick);
      }
    });
  }, 10);
}

// =========================
// FILE ACTIONS: download / delete / favorite
// =========================

// Tombol download
function downloadFile(path) {
  window.location.href = `/download/${path}`;
}

// Tombol delete
function deleteFile(path, event) {
  if (!confirm("Yakin ingin menghapus file ini?")) return;

  fetch('/delete-file', {
    method: 'POST',
    headers: {'Content-Type':'application/x-www-form-urlencoded'},
    body: `path=${encodeURIComponent(path)}`
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      // hapus card dari DOM tanpa refresh
      const card = event.target.closest('.card');
      if (card) card.remove();
    } else {
      alert("Gagal menghapus file: " + (res.error || ""));
    }
  });
}

// Tombol favorit (redirect versi aman)
document.addEventListener("click", function(e){
  const btn = e.target.closest(".favorite-btn");
  if (!btn) return;

  const path = btn.dataset.path;
  if (!path) return;

  // redirect ke backend favorite
  window.location.href = `/favorite?path=${encodeURIComponent(path)}`;
});


// Preview button attach (jika pakai data-attribute di index.html)
document.querySelectorAll('.preview-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    openPreview(btn.dataset.filename, btn.dataset.path);
  });
});


// GLOBAL
let currentPreviewURL = "";
let previewType = null;
let scale = 1;


// =========================
// OPEN PREVIEW
// =========================
function openPreview(filename, reqPath) {
    const modal = document.getElementById("previewModal");
    const content = document.getElementById("previewContent");
    const filenameEl = document.getElementById("previewFilename");
    const downloadLink = document.getElementById("downloadFile");
    const newTabLink = document.getElementById("openNewTab");
    const pageIndicator = document.getElementById("pageIndicator");

    content.innerHTML = `<div class="preview-placeholder">Loading preview...</div>`;
    filenameEl.textContent = filename;
    scale = 1;
    currentPage = 1;
    totalPages = 1;
    pdfDoc = null;

    fetch(`/preview-info?path=${encodeURIComponent(reqPath)}`)
        .then(r => r.json())
        .then(info => {
            if (info.error) { 
                content.innerHTML = "<p>File tidak ditemukan.</p>"; 
                pageIndicator.textContent = "0/0";
                return; 
            }

            const url = `/uploads/${info.path}`;
            currentPreviewURL = url;
            downloadLink.href = url;
            downloadLink.download = filename;
            newTabLink.href = url;

            content.innerHTML = "";
            const mime = info.mime || "";

            // IMAGE
            if (mime.startsWith("image/")) {
                const img = document.createElement("img");
                img.id = "pv";
                img.src = url;
                img.style.maxWidth = "100%";
                img.style.maxHeight = "100%";
                content.appendChild(img);
                pageIndicator.textContent = "1/1";

            // PDF
            } else if (mime === "application/pdf") {
              const iframe = document.createElement("iframe");
              iframe.id = "pv";
              iframe.src = url;
              iframe.style.width = "100%";
              iframe.style.height = "100%";
              iframe.style.border = "none";

              content.appendChild(iframe);
              pageIndicator.textContent = "1/1";

            // Word, Excel, PowerPoint (Office Online Viewer)
            } else if (
                filename.endsWith(".docx") ||
                filename.endsWith(".xlsx") ||
                filename.endsWith(".pptx")
            ) {
                const iframe = document.createElement("iframe");
                iframe.id = "pv";
                iframe.src = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(location.origin + url)}`;
                iframe.style.border = "none";
                iframe.style.width = "100%";
                iframe.style.height = "100%";
                content.appendChild(iframe);
                pageIndicator.textContent = "1/1";

            // CSV / TXT
            } else if (
                mime === "text/csv" || mime === "text/plain" ||
                filename.endsWith(".csv") || filename.endsWith(".txt")
            ) {
                const div = document.createElement("pre");
                div.id = "pv";
                content.appendChild(div);
                fetch(url)
                    .then(r => r.text())
                    .then(txt => { div.textContent = txt; pageIndicator.textContent = "1/1"; });

            // Video
            } else if (mime.startsWith("video/")) {
                const video = document.createElement("video");
                video.id = "pv";
                video.src = url;
                video.controls = true;
                video.style.maxWidth = "100%";
                video.style.maxHeight = "100%";
                content.appendChild(video);
                pageIndicator.textContent = "1/1";

            // Audio
            } else if (mime.startsWith("audio/")) {
                const audio = document.createElement("audio");
                audio.id = "pv";
                audio.src = url;
                audio.controls = true;
                content.appendChild(audio);
                pageIndicator.textContent = "1/1";

            } else {
                content.innerHTML = "<p>Preview tidak tersedia</p>";
                pageIndicator.textContent = "0/0";
            }

            modal.style.display = "flex";
        });
}

// =========================
// BOOKMARK PLACEHOLDER
// =========================
document.getElementById("bookmarkBtn").addEventListener("click", () => {
    alert("Bookmark ditambahkan! (belum implementasi backend)");
});

// SHARE
document.addEventListener("click", function(e){
  const btn = e.target.closest(".share-btn");
  if(!btn) return;

  const path = btn.dataset.path;

  fetch("/share", {
    method: "POST",
    headers: {"Content-Type":"application/x-www-form-urlencoded"},
    body: `path=${encodeURIComponent(path)}`
  })
  .then(r => r.json())
  .then(res => {
    if(res.success){
      navigator.clipboard.writeText(res.url);
      alert("Link berhasil dibuat & disalin:\n\n" + res.url);
    } else {
      alert("Gagal membuat link share");
    }
  });
});

// =========================
// CLOSE PREVIEW
// =========================
document.getElementById("previewCloseBtn").addEventListener("click", () => {
    document.getElementById("previewModal").style.display = "none";
    document.getElementById("previewContent").innerHTML = "";
    currentPreviewURL = "";
    scale = 1;
    pdfDoc = null;
    currentPage = 1;
    totalPages = 1;
});

// =========================
// ESC key
// =========================
document.addEventListener("keydown", (e) => { if(e.key==="Escape") document.getElementById("previewCloseBtn").click(); });

// =========================
// TOMBOL PREVIEW LISTENER (index.html)
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('.preview-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            openPreview(btn.dataset.filename, btn.dataset.path);
        });
    });
});

//  Tombol Share
document.addEventListener("click", function(e){
  const btn = e.target.closest(".share-btn");
  if(!btn) return;

  const path = btn.dataset.path;
  alert("Nanti link share untuk:\n" + path);
});

// helper error
function showError(msg) {
    const box = document.getElementById("previewContent");
    box.innerHTML = `<div class="preview-error">${msg}</div>`;
}
function setControlState(enabled) {
  ["zoomIn", "zoomOut", "prevPage", "nextPage"].forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = !enabled;
    btn.style.opacity = enabled ? "1" : "0.4";
    btn.title = enabled ? "" : "Fitur tidak tersedia untuk preview PDF";
  });
}
