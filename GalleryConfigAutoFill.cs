// GalleryConfigAutoFill.cs
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using VRC.SDKBase;

[CustomEditor(typeof(GalleryConfig))]
public class GalleryConfigAutoFill : Editor
{
    // 既定値（必要ならInspectorで書き換えてOK）
    private string root = "https://kuro-iro-yagi.github.io/kuroyagi.github.io/gallery";
    private int thumbPages = 13;  // ≤ 13
    private int fullCount   = 208; // PC/Mobile とも同数

    public override void OnInspectorGUI()
    {
        base.OnInspectorGUI();
        var cfg = (GalleryConfig)target;

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("=== Auto Fill (Editor-only) ===", EditorStyles.boldLabel);

        root       = EditorGUILayout.TextField("Root", root);
        thumbPages = EditorGUILayout.IntSlider("Thumb Pages", thumbPages, 1, 13);
        fullCount  = EditorGUILayout.IntSlider("Full Count", fullCount, 1, 208);

        if (GUILayout.Button("URLを自動生成して流し込む"))
        {
            Undo.RecordObject(cfg, "Auto Fill GalleryConfig");

            // サムネ（アトラス）
            cfg.thumbAtlasPages = new VRCUrl[thumbPages];
            for (int i=0; i<thumbPages; i++)
            {
                int pageNo = i + 1;
                string url = $"{root}/thumbs_page_{pageNo.ToString("0000")}.png";
                cfg.thumbAtlasPages[i] = new VRCUrl(url);
            }

            // PCフル
            cfg.fullPc = new VRCUrl[fullCount];
            for (int i=0; i<fullCount; i++)
            {
                int num = i + 1;
                string url = $"{root}/full_pc/{num.ToString("000")}.png";
                cfg.fullPc[i] = new VRCUrl(url);
            }

            // モバイルフル
            cfg.fullMobile = new VRCUrl[fullCount];
            for (int i=0; i<fullCount; i++)
            {
                int num = i + 1;
                string url = $"{root}/full_mobile/{num.ToString("000")}.png";
                cfg.fullMobile[i] = new VRCUrl(url);
            }

            cfg.Recalc();
            EditorUtility.SetDirty(cfg);
            Debug.Log($"[GalleryConfigAutoFill] 生成完了: thumbs={thumbPages}, full={fullCount}");
        }
    }
}
#endif
