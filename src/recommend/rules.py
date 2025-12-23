def make_recommendation(uvi, humidity, kondisi_kulit, reaksi_kulit, has_sunscreen: bool, conflict_notes: str):
    am, pm, warn = [], [], []

    kondisi = (kondisi_kulit or "").lower()
    reaksi = (reaksi_kulit or "").lower()

    # UV → aksi sunscreen
    if uvi is not None:
        try:
            u = float(uvi)
        except:
            u = None
        if u is not None:
            if u >= 8:
                am.append(f"UV sangat tinggi ({u}) → sunscreen wajib + reapply lebih sering.")
            elif u >= 3:
                am.append(f"UV sedang ({u}) → sunscreen wajib.")
            else:
                am.append(f"UV rendah ({u}) → sunscreen tetap disarankan.")

            if u >= 3 and not has_sunscreen:
                warn.append("Stok sunscreen tidak ditemukan di inventory → pertimbangkan beli/siapkan sunscreen.")

    # Humidity + kondisi kulit
    if humidity is not None:
        try:
            h = float(humidity)
        except:
            h = None
        if h is not None:
            if h <= 45 or "kering" in kondisi:
                am.append("Kelembapan rendah / kulit kering → moisturizer lebih rich.")
            else:
                am.append("Kelembapan cukup → moisturizer gel/light cukup.")

    # Reaksi kulit → recovery
    if "kemerahan" in reaksi or "irit" in reaksi:
        pm.append("Recovery night: fokus soothing + hydrating, tunda active kuat.")
        warn.append("Kulit sedang reaktif → hindari exfoliant/retinoid dulu.")
    else:
        pm.append("Ikuti rutinitas malam sesuai rencana (jika ada).")

    if conflict_notes:
        warn.append(f"Catatan ingredients: {conflict_notes}")

    return " | ".join(am), " | ".join(pm), " | ".join(warn)