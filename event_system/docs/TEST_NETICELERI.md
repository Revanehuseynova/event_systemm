# Test ssenariləri və nəticələr

İşə salmaq: `python -m unittest discover -v`

| # | Ssenari | Növ | Gözlənilən nəticə | Nəticə |
|---|---------|-----|-------------------|--------|
| 1 | Düzgün məlumatla tədbir yaratmaq | Normal | 201, qeydiyyat sayı 0 | ✅ |
| 2 | Boş ad ilə tədbir yaratmaq | Xəta | 400 | ✅ |
| 3 | Keçmiş tarix, limit=0, yanlış tarix formatı | Xəta | 400 | ✅ |
| 4 | Ada / kateqoriyaya görə axtarış, nəticəsiz axtarış | Normal | Uyğun siyahı, boş siyahı | ✅ |
| 5 | Tədbiri redaktə etmək və silmək | Normal | Yenilənir, sonra 404 | ✅ |
| 6 | Limiti cari qeydiyyat sayından aşağı salmaq | Xəta | 400 | ✅ |
| 7 | Uğurlu qeydiyyat və say artımı | Normal | 201, registered=1 | ✅ |
| 8 | Təkrar qeydiyyat | Xəta | 409 | ✅ |
| 9 | Limit dolduqda qeydiyyat | Xəta | 3-cü cəhd 409 | ✅ |
| 10 | Ləğvdən sonra yer boşalır | Normal | Növbəti istifadəçi qeydiyyatdan keçir | ✅ |
| 11 | 8 paralel sorğu, limit 3 | Yarış halı | Dəqiq 3 qeydiyyat | ✅ |
| 12 | SQL injection cəhdi | Təhlükəsizlik | Cədvəl salamat qalır | ✅ |
| 13 | Yanlış e-poçt, yanlış JSON | Xəta | 400 | ✅ |
| 14 | Statistika hesablamaları | Normal | Düzgün say və sıralama | ✅ |
| 15 | Limit dolu olsa belə təkrar qeydiyyat mesajı | Xəta | 409 + "artıq qeydiyyatdan keçmisiniz" | ✅ |
| 16 | Yanlış HTTP metodu | Xəta | 405 + JSON mesaj | ✅ |

**Yekun:** 16 test, 16 uğurlu.
