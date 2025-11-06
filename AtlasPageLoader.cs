using UdonSharp;
using UnityEngine;
using UnityEngine.UI;
using VRC.SDK3.Image;
using VRC.SDKBase;
using VRC.Udon.Common.Interfaces;
using TMPro;

public class AtlasPageLoader : UdonSharpBehaviour
{
    [Header("UI: 4x4 サムネ（左上→右→下の順に16個）")]
    public RawImage[] thumbSlots16;

    [Header("UI: 読み込み中オーバーレイ")]
    public GameObject loadingOverlay;
    public TMP_Text loadingText;

    private VRCImageDownloader _downloader;

    // 直近にDLしたアトラス画像（RawImageに直張りする）
    private Texture2D _atlasTex;

    // 4x4 のUV（RawImage.uvRect に入れる）
    private Rect[] _uvRects;

    // ページ管理（デバッグ用）
    private int _currentPage = -1;

    // タイムアウト検知
    private bool _waiting;

    void Start()
    {
        if (_downloader == null) _downloader = new VRCImageDownloader();

        // 4x4のUVを上から順に生成
        if (_uvRects == null)
        {
            _uvRects = new Rect[16];
            int i = 0;
            for (int row = 0; row < 4; row++)
            {
                for (int col = 0; col < 4; col++)
                {
                    // RawImageは左下原点。上から貼りたいのでYは 1 - (row+1)*0.25
                    _uvRects[i] = new Rect(col * 0.25f, 1f - (row + 1) * 0.25f, 0.25f, 0.25f);
                    i++;
                }
            }
        }
    }

    /// <summary>
    /// アトラス1枚をDLして、16個のRawImageにUVで切り出して表示するのよ。
    /// </summary>
    public void LoadPage(VRCUrl atlasUrl, int pageIndex)
    {
        if (_downloader == null) _downloader = new VRCImageDownloader(); // 念押しの保険
        _currentPage = pageIndex;

        if (loadingOverlay != null) loadingOverlay.SetActive(true);
        if (loadingText != null) loadingText.text = "読み込み中…";

        // --- 入力ガード（ここで落ちないように丁寧に） ---
        if (thumbSlots16 == null || thumbSlots16.Length < 16)
        {
            if (loadingText != null) loadingText.text = "設定エラー：サムネ16枠が未設定";
            Debug.LogError("[Atlas] thumbSlots16 < 16");
            return;
        }
        if (atlasUrl == null)
        {
            if (loadingText != null) loadingText.text = "設定エラー：サムネURLが null";
            Debug.LogError("[Atlas] url is NULL");
            return;
        }
        string u = atlasUrl.Get();
        if (u == null || u.Length == 0)
        {
            if (loadingText != null) loadingText.text = "設定エラー：サムネURLが空";
            Debug.LogError("[Atlas] url is EMPTY");
            return;
        }

        // --- ダウンロード（Material を使わず、結果テクスチャを受け取る） ---
        var info = new TextureInfo();
        // 必要に応じて画質系を設定（省略可）
        info.GenerateMipMaps = true;
        info.AnisoLevel = 1;
        info.FilterMode = FilterMode.Bilinear;
        info.WrapModeU = TextureWrapMode.Clamp;
        info.WrapModeV = TextureWrapMode.Clamp;
        info.WrapModeW = TextureWrapMode.Clamp;

        _waiting = true;
        Debug.Log("[Atlas] Download start: " + u + " (page " + pageIndex + ")");
        _downloader.DownloadImage(atlasUrl, null, (IUdonEventReceiver)this, info); // ★ Material=null

        // 10秒応答なしならユーザーに見える形で切るのよ
        SendCustomEventDelayedSeconds(nameof(_TimeoutCheck), 10f);
    }

    public void _TimeoutCheck()
    {
        if (!_waiting) return;
        if (loadingText != null) loadingText.text = "読み込み停止：応答なし（URL/回線/権限）";
        Debug.LogError("[Atlas] TIMEOUT: no success/error callback");
    }

    public override void OnImageLoadSuccess(IVRCImageDownload result)
    {
        _waiting = false;

        // コールバックの result.Result が Texture2D（Material不使用ルート）
        Texture2D tex = null;
        if (result != null) tex = result.Result;
        if (tex == null)
        {
            OnImageLoadError(result);
            return;
        }
        Debug.Log("[Atlas] SUCCESS: " + tex.width + "x" + tex.height); // ★サイズ確認
        _atlasTex = tex;

        // ★残りは分割（従来通り）
        int n = thumbSlots16 != null ? thumbSlots16.Length : 0;
        for (int i = 0; i < n; i++)
        {
            var img = thumbSlots16[i];
            if (img == null) continue;

            img.texture = _atlasTex;                 // ★ 直接テクスチャを張る
            if (_uvRects != null && i < _uvRects.Length) img.uvRect = _uvRects[i];
            img.enabled = true;
        }

        if (loadingOverlay != null) loadingOverlay.SetActive(false);
        if (loadingText != null) loadingText.text = "";
    }

    public override void OnImageLoadError(IVRCImageDownload result)
    {
        _waiting = false;

        string msg = "(unknown)";
        if (result != null) msg = result.ErrorMessage;

        if (loadingOverlay != null) loadingOverlay.SetActive(true);
        if (loadingText != null) loadingText.text = "読み込み失敗：" + msg;

        Debug.LogError("[Atlas] download failed: " + msg);
    }

    public int GetPageIndex()
    {
        return _currentPage;
    }
}
