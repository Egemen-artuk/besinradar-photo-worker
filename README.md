# BesinRadar fotoğraf temizleyici

Kullanıcıların çektiği ürün ön yüzü fotoğraflarının arka planını siler.
GitHub'ın ücretsiz sunucusunda 30 dakikada bir kendiliğinden çalışır; senin
bilgisayarının açık olması gerekmez.

Akış:

1. Kullanıcı ön yüzü çeker → sunucu (Supabase) yapay zekâ ile kontrol eder ve ürüne göre kırpar.
2. Fotoğraf "onay bekliyor" olarak kaydedilir (uygulamada henüz görünmez).
3. Bu işçi bekleyen fotoğrafların arka planını siler (rembg, `isnet-general-use` modeli).
4. Sen besinradar.app/admin sayfasında kırpılmış ya da arka planı temiz halini seçip **Onayla** dersin.
5. Onaylanan fotoğraf ürünün resmi olur.

## Kurulum (bir kez, ~10 dakika)

1. github.com'da yeni bir depo oluştur, adı örneğin `besinradar-photo-worker`.
   **Public** seçersen GitHub Actions dakikaları tamamen ücretsiz olur (kod bu klasördeki
   birkaç dosyadan ibaret, gizli bir şey içermez; anahtarlar ayrı ve şifreli saklanır).
   Private da olur: ayda 2000 dakika ücretsiz, bu iş için genelde yeterli.
2. Depoya bu klasördeki `README.md`, `clean_photos.py` ve `requirements.txt` dosyalarını yükle
   (depo sayfasında *Add file → Upload files*, dosyaları sürükle, *Commit changes*).
   Sonra *Add file → Create new file* de; dosya adı kutusuna tam olarak
   `.github/workflows/clean-photos.yml` yaz, bu klasördeki `clean-photos.yml` dosyasının
   içeriğini kopyalayıp yapıştır ve *Commit changes* de.
3. Depoda *Settings → Secrets and variables → Actions → New repository secret*:
   - `SUPABASE_URL` = `https://ywtsbvzmvovmkjzyfzqi.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = Supabase → Project Settings → API Keys → **secret** (service_role) anahtarı.
     Bu anahtarı sadece buraya yapıştır; uygulamaya ya da sohbete koyma.
4. *Actions* sekmesinde iş akışını etkinleştir, *Urun fotograflarini temizle → Run workflow*
   ile bir kez elle çalıştırıp dene. İlk çalıştırma modeli indirdiği için 2-3 dakika sürebilir.

## Notlar

- Bekleyen fotoğraf yoksa iş birkaç saniyede biter (kurulum adımları atlanır).
- GitHub, 60 gün hiç değişiklik olmayan depolarda zamanlanmış işleri durdurur; iş akışı
  bunu önlemek için gerektiğinde küçük bir `.heartbeat` dosyası günceller.
- Arka plan silme başarısız olursa (model ürünü bulamazsa) yönetim sayfasında kırpılmış
  orijinal yine seçilebilir.
