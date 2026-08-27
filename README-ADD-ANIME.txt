========================================
HindiAnimestuff — SOURCE PROJECT
========================================

Yeh SOURCE hai. Deploy folder nahi.

FOLDER STRUCTURE
----------------
  data.json          ← yahan naya anime add karo
  generate.py        ← pages banata hai
  templates/         ← HTML design
  assets/            ← css/js/logo
  output/            ← generate ke baad yahan site banti hai (auto)

NAYA ANIME ADD KARNA
--------------------
1) linkcleaner.js se:
     node linkcleaner.js tosite site-input.txt
   → site-item.json milega

2) site-item.json ka object data.json ke "items" array me paste karo
   (last item ke baad comma, naya object)

3) Generate:
     cd is-folder-me
     pip install jinja2   # pehli baar
     python3 generate.py

4) Deploy:
     # firebase.json me public = "output" rakho
     firebase deploy --only hosting

     YA output/ ke files apne hosting folder me copy karke deploy

SITE-ITEM.JSON KA FORMAT
------------------------
{
  "id": "my-anime-s1",
  "category": "anime",
  "season": "Season 1",
  "title": "My Anime",
  "poster": "https://...",
  "episode_links": {
    "01": { "1080p": "https://icy-feather-...workers.dev/?id=...&name=..." },
    "02": { "1080p": "https://..." }
  },
  ...
}

IMPORTANT
---------
- assets/data.js mat edit karo — generate.py banata hai
- assets/download-data.js mat edit karo — generate.py banata hai
- Sirf data.json edit karo
