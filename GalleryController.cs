using UdonSharp;
using UnityEngine;
using UnityEngine.UI;
using VRC.SDK3.Image;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;
using TMPro;

public class GalleryController : UdonSharpBehaviour
{
    [Header("Config（URL配列を事前オートフィル済みのもの）")]
    public GalleryConfig config;

    [Header("サムネページング")]
    public AtlasPageLoader atlasLoader;
    public Button prevPageBtn;       // ★Inspector: OnClick → PrevPage()
    public Button nextPageBtn;       // ★Inspector: OnClick → NextPage()
    public TMP_Text pageLabel;       // 「1 / 13」のような表示

    [Header("拡大表示パネル")]
    public GameObject fullscreenPanel;
    public RawImage fullscreenImage;
    public GameObject fullscreenLoadingOverlay;
    public TMP_Text fullscreenLoadingText;
    public Button closeFullscreenBtn; // ★Inspector: OnClick → CloseFullscreen()

    [Header("再読み込み")]
    public Button reloadBtn;          // ★Inspector: OnClick → ReloadPage()

    [Header("Editor検証用（任意）")]
    [SerializeField] private bool forceMobileInEditor = false; // Editor再生でモバイル挙動を試す用

    private VRCImageDownloader _downloader;
    private int _pageIndex;          // 0-based
    private int _mobileMode;         // 0=PC, 1=Mobile(Android/iOS)

    void Start()
    {
        Debug.Log("[Gallery] Start");
        if (_downloader == null) _downloader = new VRCImageDownloader();
        DetectPlatform();
        GoToPage(0);
    }

    /// <summary>
    /// 実行プラットフォームからモバイル/PCを判定（Application.platformベース）
    /// </summary>
    private void DetectPlatform()
    {
        // ビルドターゲットで判定：Quest/Androidビルドならモバイル扱い
        // （Udonでは Application.platform は使えないため）
        #if UNITY_ANDROID
            _mobileMode = 1;
        #else
            _mobileMode = 0;
        #endif

        // Editorでモバイル挙動を試したいときの手動上書き
        #if UNITY_EDITOR
            if (forceMobileInEditor) _mobileMode = 1;
        #endif
    }

    /// <summary>
    /// 指定ページ（0-based）に移動。サムネアトラスを1枚DLして表示。
    /// </summary>
    public void GoToPage(int idx)
    {
        if (config == null) return;

        int totalPages = config.totalThumbPages;
        if (totalPages < 1) totalPages = 1;

        int last = totalPages - 1;
        if (idx < 0) idx = 0;
        if (idx > last) idx = last;
        _pageIndex = idx;

        if (pageLabel != null)
        {
            // U#は文字列補間より連結が安全
            pageLabel.text = (_pageIndex + 1).ToString() + " / " + config.totalThumbPages;
        }

        if (atlasLoader != null)
        {
            if (config.thumbAtlasPages != null)
            {
                if (_pageIndex >= 0 && _pageIndex < config.thumbAtlasPages.Length)
                {
                    VRCUrl url = config.thumbAtlasPages[_pageIndex];
                    atlasLoader.LoadPage(url, _pageIndex);
                }
            }
        }
    }

    // ======= ここからは Inspector の OnClick で直接呼ぶ公開メソッド =======

    public void PrevPage()
    {
        GoToPage(_pageIndex - 1);
    }

    public void NextPage()
    {
        GoToPage(_pageIndex + 1);
    }

    public void ReloadPage()
    {
        GoToPage(_pageIndex);
    }

    /// <summary>
    /// サムネ（0..15 のインデックス）を押したときに呼ぶ。Inspectorで各ボタンから指定。
    /// </summary>
    public void OnThumbnailClicked(int index0to15)
    {
        if (config == null) return;

        int total = config.totalImages;
        if (total <= 0) return;

        if (index0to15 < 0) return;
        int globalIdx = _pageIndex * 16 + index0to15;
        if (globalIdx < 0) return;
        if (globalIdx >= total) return;

        VRCUrl url;
        if (_mobileMode == 1)
        {
            url = config.fullMobile[globalIdx];
        }
        else
        {
            url = config.fullPc[globalIdx];
        }

        ShowFullscreen(url);
    }

    /// <summary>
    /// 拡大表示を開始。画像DL完了までは「読み込み中…」を表示。
    /// </summary>
    private void ShowFullscreen(VRCUrl url)
    {
        if (_downloader == null) _downloader = new VRCImageDownloader(); // 念押し

        if (fullscreenPanel != null) fullscreenPanel.SetActive(true);
        if (fullscreenLoadingOverlay != null) fullscreenLoadingOverlay.SetActive(true);
        if (fullscreenLoadingText != null) fullscreenLoadingText.text = "読み込み中…";
        if (fullscreenImage != null) fullscreenImage.texture = null;

        if (url == null)
        {
            if (fullscreenLoadingText != null) fullscreenLoadingText.text = "設定エラー: 画像URLが null";
            Debug.LogError("[Full] url is NULL");
            return;
        }
        string u = url.Get();
        if (u == null || u.Length == 0)
        {
            if (fullscreenLoadingText != null) fullscreenLoadingText.text = "設定エラー: 画像URLが空文字";
            Debug.LogError("[Full] url string is EMPTY");
            return;
        }

        var texInfo = new TextureInfo();
        Debug.Log("[Full] Download start: " + u);
        _downloader.DownloadImage(url, null, (IUdonEventReceiver)this, texInfo); // ★ Material=null
    }

    /// <summary>
    /// 拡大画像のDL成功時に、Materialに入ったテクスチャをRawImageに反映。
    /// </summary>
    public override void OnImageLoadSuccess(IVRCImageDownload result)
    {
        if (fullscreenImage != null)
        {
            Texture2D tex = null;
            if (result != null) tex = result.Result;
            if (tex != null) fullscreenImage.texture = tex; // ★ 直接テクスチャを貼る
         }
        if (fullscreenLoadingOverlay != null) fullscreenLoadingOverlay.SetActive(false);
        if (fullscreenLoadingText != null) fullscreenLoadingText.text = "";
    }

    public override void OnImageLoadError(IVRCImageDownload result)
    {
        if (fullscreenLoadingOverlay != null) fullscreenLoadingOverlay.SetActive(true);
        if (fullscreenLoadingText != null) fullscreenLoadingText.text = "読み込み失敗…";
    }

    public void CloseFullscreen()
    {
        if (fullscreenPanel != null) fullscreenPanel.SetActive(false);
    }
    // ==== サムネクリック用の引数なしイベント（SendCustomEvent用） ====
    // 左上0 → 右へ… → 下の行 という並びで16個
    public void Thumb_00() { OnThumbnailClicked(0); }
    public void Thumb_01() { OnThumbnailClicked(1); }
    public void Thumb_02() { OnThumbnailClicked(2); }
    public void Thumb_03() { OnThumbnailClicked(3); }
    public void Thumb_04() { OnThumbnailClicked(4); }
    public void Thumb_05() { OnThumbnailClicked(5); }
    public void Thumb_06() { OnThumbnailClicked(6); }
    public void Thumb_07() { OnThumbnailClicked(7); }
    public void Thumb_08() { OnThumbnailClicked(8); }
    public void Thumb_09() { OnThumbnailClicked(9); }
    public void Thumb_10() { OnThumbnailClicked(10); }
    public void Thumb_11() { OnThumbnailClicked(11); }
    public void Thumb_12() { OnThumbnailClicked(12); }
    public void Thumb_13() { OnThumbnailClicked(13); }
    public void Thumb_14() { OnThumbnailClicked(14); }
    public void Thumb_15() { OnThumbnailClicked(15); }

}