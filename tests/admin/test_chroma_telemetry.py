def test_disable_chroma_telemetry_patches_incompatible_posthog_capture(monkeypatch):
    import chromadb.telemetry.product.posthog as chroma_posthog
    from tools.rag.chroma_telemetry import disable_chroma_telemetry

    calls = []

    def noisy_direct_capture(self, event):
        calls.append((self, event))
        raise TypeError("capture() takes 1 positional argument but 3 were given")

    monkeypatch.setattr(chroma_posthog.Posthog, "_direct_capture", noisy_direct_capture)

    disable_chroma_telemetry()

    chroma_posthog.Posthog._direct_capture(object(), object())

    assert calls == []
    assert chroma_posthog.posthog.disabled is True
