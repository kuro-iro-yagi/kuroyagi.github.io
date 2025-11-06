// Assets/★追加/001_スクリプト/GalleryConfig.cs
using UdonSharp;
using UnityEngine;
using VRC.SDKBase;
using VRC.SDK3.Image;
using UnityEngine.UI;

public class GalleryConfig : UdonSharpBehaviour
{
    [Header("決め打ちURL（Editor拡張で自動充填）")]
    public VRCUrl[] thumbAtlasPages; // ≤ 13
    public VRCUrl[] fullPc;          // ≤ 208
    public VRCUrl[] fullMobile;      // ≤ 208

    // 総数（念のため Inspector で確認しやすく）
    public int totalThumbPages;
    public int totalImages;

    public void Recalc()
    {
        totalThumbPages = (thumbAtlasPages != null) ? thumbAtlasPages.Length : 0;
        totalImages = Mathf.Min(
            (fullPc != null) ? fullPc.Length : 0,
            (fullMobile != null) ? fullMobile.Length : 0
        );
    }
}
