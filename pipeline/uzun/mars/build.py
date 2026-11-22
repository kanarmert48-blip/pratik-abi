"""Mars uzun video: zaman çizelgesi + ses + render.
python3 build.py timeline | audio | frames t1,t2 | part i n | concat"""
import json, math, re, sys, subprocess, difflib
from pathlib import Path
import numpy as np, soundfile as sf
import cairo
import shots
from shots import label, fin, ease
from vec import *
from plan import PLAN, CHAPTERS

ROOT = Path(__file__).parent
FPS = 30
SR = 24000
LEAD = 0.35         # videonun başında
PGAP = 0.30         # paragraflar arası ek sessizlik
CGAP = 1.50         # bölüm geçişi (sessiz görüntü + bölüm adı)
TAIL = 2.2


def norm(s):
    s = s.replace('I', 'ı').replace('İ', 'i').lower()
    return re.sub(r"[^a-zçğıöşüâîû0-9]", "", s)


def build_timeline():
    P = json.load(open(ROOT / 'paras.json'))
    WS = json.load(open(ROOT / 'words_sec.json'))
    pieces, words, paras, chapters = [], [], {}, []
    g = LEAD
    for sec in range(17):
        a, sr = sf.read(ROOT / f'ses/sec{sec:02d}.wav'); assert sr == SR
        ws = WS[str(sec)]
        sp = [p for p in P if p['sec'] == sec]
        # script kelimeleri (paragraf, cümle, metin)
        sw = []
        for p in sp:
            sents = re.split(r'(?<=[.?!…])\s+', p['t'])
            for si, s in enumerate(sents):
                for w in s.split():
                    sw.append({'pid': p['id'], 'si': si, 'w': w})
        # karakter hizalaması
        def charmap(tokens):
            s, idx = '', []
            for i, t in enumerate(tokens):
                n = norm(t); s += n; idx += [i] * len(n)
            return s, idx
        A_, ai = charmap([x['w'] for x in sw])
        B_, bi = charmap([x['w'] for x in ws])
        sm = difflib.SequenceMatcher(None, A_, B_, autojunk=False)
        a2b = {}
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                a2b[blk.a + k] = blk.b + k
        # her script kelimesine zaman
        starts = [None] * len(sw); ends = [None] * len(sw)
        pos = 0
        for i, x in enumerate(sw):
            n = len(norm(x['w']))
            cs = [a2b[c] for c in range(pos, pos + n) if c in a2b]
            if cs:
                starts[i] = ws[bi[cs[0]]]['s']; ends[i] = ws[bi[cs[-1]]]['e']
            pos += n
        # boşlukları enterpolasyonla doldur
        known = [i for i in range(len(sw)) if starts[i] is not None]
        for i in range(len(sw)):
            if starts[i] is None:
                prv = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
                t0 = ends[prv] if prv is not None else 0.0
                t1 = starts[nxt] if nxt is not None else len(a) / SR
                cnt = (nxt if nxt is not None else len(sw)) - (prv if prv is not None else -1)
                q = (i - (prv if prv is not None else -1)) / cnt
                starts[i] = t0 + (t1 - t0) * q; ends[i] = starts[i] + (t1 - t0) / cnt * 0.9
        # paragraf kesim noktaları
        pids = [p['id'] for p in sp]
        cuts = [0.0]
        for k in range(1, len(pids)):
            i0 = next(i for i, x in enumerate(sw) if x['pid'] == pids[k])
            cuts.append((ends[i0 - 1] + starts[i0]) / 2)
        cuts.append(len(a) / SR)
        if sec > 0:
            chapters.append({'sec': sec, 'start': g, 'end': g + CGAP, 'title': CHAPTERS[sec]})
            g += CGAP
        for k, pid in enumerate(pids):
            c0, c1 = cuts[k], cuts[k + 1]
            pieces.append({'sec': sec, 'a': c0, 'b': c1, 'g': g})
            paras[pid] = {'start': g - (CGAP if (k == 0 and sec > 0) else 0), 'vstart': g, 'sec': sec, 'k': k}
            for i, x in enumerate(sw):
                if x['pid'] == pid:
                    words.append(dict(x, s=g + starts[i] - c0, e=g + ends[i] - c0, sec=sec))
            g += (c1 - c0) + (PGAP if k < len(pids) - 1 else 0.0)
        g += 0.15
    total = g + TAIL
    # sahneler
    shots_ = []
    for pid in sorted(PLAN):
        for j, (si, nm, kw) in enumerate(PLAN[pid]):
            if j == 0:
                st = paras[pid]['start'] if pid > 1 else 0.0
            else:
                st = min(w['s'] for w in words if w['pid'] == pid and w['si'] == si) - 0.12
            shots_.append({'pid': pid, 'name': nm, 'kw': kw, 'start': round(st, 3)})
    for k in range(len(shots_)):
        shots_[k]['end'] = shots_[k + 1]['start'] if k + 1 < len(shots_) else total
    # uzun planları cümle başlarından farklı kadrajlarla böl (plan süresi 3–7 sn)
    sent_starts = sorted({min(w['s'] for w in words if (w['pid'], w['si']) == key) for key in {(w['pid'], w['si']) for w in words}})
    out = []
    has_lab = ('lab', 'count', 'years', 'labs', 'compare', 'gauge', 'labels', 'earth_arrow')
    for s in shots_:
        s['base'], s['bend'] = s['start'], s['end']
        d = s['end'] - s['start']
        if d <= 8.0:
            s['frame'] = 'wide'; out.append(s); continue
        cuts, last = [], s['start']
        for ss in sent_starts:
            c0 = ss - 0.12
            if c0 - last >= 3.2 and s['end'] - c0 >= 3.2:
                if c0 - last >= 4.5 or (s['end'] - last) > 7.5:
                    cuts.append(c0); last = c0
        bounds = [s['start']] + cuts + [s['end']]
        variants = ['wide', 'close', 'wide2', 'close'] if not any(k in s['kw'] for k in has_lab) else ['wide', 'wide2', 'wide', 'wide2']
        for j in range(len(bounds) - 1):
            ns = dict(s, start=round(bounds[j], 3), end=round(bounds[j + 1], 3), frame=variants[j % 4])
            out.append(ns)
    shots_ = out
    # altyazı parçaları
    subs = []
    bad_end = {'ve', 'ile', 'bir', 'de', 'da', 'ki', 'bu', 'o', 'çok', 'en', 'her', 'tek', 'kendi', 'iki', 'üç', 'birkaç', 'küçük', 'dev', 'daha', 'sadece', 'yaklaşık', 'neredeyse', 'tam', 'hatta', 'yani'}
    groups = {}
    for w in words:
        groups.setdefault((w['pid'], w['si']), []).append(w)
    for key, ws_ in groups.items():
        n = len(ws_)
        txt = lambda i, j: ' '.join(x['w'] for x in ws_[i:j])
        tot_len = len(txt(0, n))
        k_min = max(1, math.ceil(tot_len / 32))
        best = None
        for kk in (k_min, k_min + 1):
            target = tot_len / kk
            # dp[j][m]: ilk j kelime m parçada en iyi maliyet
            INF = 1e9
            dp = [[(INF, -1)] * (kk + 1) for _ in range(n + 1)]
            dp[0][0] = (0, -1)
            for j in range(1, n + 1):
                for m in range(1, kk + 1):
                    for i in range(m - 1, j):
                        if dp[i][m - 1][0] >= INF:
                            continue
                        L_ = len(txt(i, j))
                        if L_ > 32 and j - i > 1:
                            continue
                        cost = (L_ - target) ** 2
                        if j < n and norm(ws_[j - 1]['w']) in bad_end:
                            cost += 400
                        if j < n and ws_[j - 1]['w'][-1] in ',:;':
                            cost -= 120
                        cost += 60
                        if j - i == 1 and n > 1:
                            cost += 150
                        cst = dp[i][m - 1][0] + cost
                        if cst < dp[j][m][0]:
                            dp[j][m] = (cst, i)
            if dp[n][kk][0] < INF and (best is None or dp[n][kk][0] < best[0]):
                cuts, j, m = [], n, kk
                while m > 0:
                    i = dp[j][m][1]; cuts.append((i, j)); j, m = i, m - 1
                best = (dp[n][kk][0], cuts[::-1])
        for i, j in best[1]:
            ch = ws_[i:j]
            subs.append({'t': ' '.join(x['w'] for x in ch), 's': ch[0]['s'] - 0.05, 'e': ch[-1]['e']})
    subs.sort(key=lambda x: x['s'])
    for k in range(len(subs)):
        nxt = subs[k + 1]['s'] if k + 1 < len(subs) else total
        subs[k]['e'] = min(nxt - 0.02, max(subs[k]['e'] + 0.45, subs[k]['e']))
    json.dump({'total': total, 'pieces': pieces, 'words': words, 'shots': shots_, 'subs': subs, 'chapters': chapters},
              open(ROOT / 'timeline.json', 'w'), ensure_ascii=False, indent=0)
    print('toplam', round(total, 1), 'sn', len(shots_), 'sahne', len(subs), 'altyazı', 'en uzun altyazı', max(len(s['t']) for s in subs))
    for s in subs:
        if len(s['t']) > 32:
            print('UZUN', s['t'])


def build_audio():
    T = json.load(open(ROOT / 'timeline.json'))
    n = int(T['total'] * SR) + SR
    v = np.zeros(n, np.float32)
    cache = {}
    for p in T['pieces']:
        if p['sec'] not in cache:
            cache[p['sec']] = sf.read(ROOT / f"ses/sec{p['sec']:02d}.wav")[0].astype(np.float32)
        a = cache[p['sec']][int(p['a'] * SR):int(p['b'] * SR)]
        i = int(p['g'] * SR)
        fade = min(240, len(a) // 4)
        a = a.copy(); a[:fade] *= np.linspace(0, 1, fade); a[-fade:] *= np.linspace(1, 0, fade)
        v[i:i + len(a)] += a
    sf.write(ROOT / 'voice.wav', v[:int(T['total'] * SR)], SR)
    # müzik: sakin + gergin (iniş ve fırtına bölümleri)
    tense = []
    for ch in T['chapters']:
        if ch['sec'] in (4, 10):
            nxt = next((c for c in T['chapters'] if c['sec'] == ch['sec'] + 1), None)
            tense.append((ch['start'], nxt['start'] if nxt else T['total']))
    tot = T['total']
    expr = '+'.join(f"between(t,{a:.2f},{b:.2f})" for a, b in tense)
    w_t = f"min(1,max(0,({'+'.join(f'clip((t-{a:.2f})/2,0,1)*clip(({b:.2f}-t)/2,0,1)' for a, b in tense)})))"
    fc = (f"[1:a]aresample=48000,atrim=0:{tot:.2f},asetpts=N/SR/TB,volume='1-{w_t}':eval=frame[m1];"
          f"[2:a]aresample=48000,atrim=0:{tot:.2f},asetpts=N/SR/TB,volume='{w_t}':eval=frame[m2];"
          f"[m1][m2]amix=inputs=2:normalize=0,lowpass=f=9000,volume=0.3,afade=t=in:d=1.5,afade=t=out:st={tot - 2.5:.2f}:d=2.5[mus];"
          f"[0:a]aresample=48000,volume=5dB,asplit=2[vo][sc];"
          f"[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=25:release=600:makeup=1[duck];"
          f"[vo][duck]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=false[out]")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ROOT / 'voice.wav'), '-stream_loop', '-1', '-i', str(ROOT / 'mars1.wav'), '-stream_loop', '-1', '-i', str(ROOT / 'mars2.wav'),
                    '-filter_complex', fc, '-map', '[out]', '-ar', '48000', '-ac', '2', str(ROOT / 'mix_raw.wav')], check=True)
    # son loudness ayarı (-14 LUFS)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(ROOT / 'mix_raw.wav'), '-af', 'loudnorm=I=-14:TP=-1:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    js = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ROOT / 'mix_raw.wav'), '-af',
                    f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,apad=pad_dur=4,atrim=0:{tot:.3f}",
                    '-ar', '48000', '-c:a', 'aac', '-b:a', '256k', str(ROOT / 'mix.m4a')], check=True)
    # ağız seviyesi
    env = []
    for f in range(int(tot * FPS) + 2):
        seg = v[int(f / FPS * SR):int((f + 1) / FPS * SR)]
        env.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    env = np.array(env); env = env / (np.percentile(env[env > 0.005], 95) + 1e-6)
    env = np.convolve(np.clip(env, 0, 1), np.ones(3) / 3, 'same')
    np.save(ROOT / 'mouth.npy', env)
    print('ses tamam', js['input_i'])


# ------------------------------------------------------------------ render
FOCUS = dict(door=(960, 900), small_room=(1300, 900), suit_reveal=(1100, 800), training_room=(1000, 800), roles=(1280, 700),
             pool=(1250, 800), lights_dim=(1100, 950), treadmill=(1300, 900), ship_float=(900, 800), window_view=(1200, 800),
             entry=(1280, 650), signal=(1280, 700), waiting=(1100, 900), first_step=(1300, 1000), helmet_close=(1100, 700),
             sky_look=(1000, 900), dust_hand=(1100, 1000), moxie=(1200, 850), ice_dig=(1300, 700), dome_water=(1300, 850),
             dome_dusk=(1280, 950), radiation=(1400, 720), cave=(1450, 1000), walk_rule=(1000, 1000), food_crate=(1100, 1000),
             soil_wash=(1500, 850), greenhouse=(1280, 1000), iss_plants=(1000, 800), tablet_msg=(1300, 800), alone_window=(1400, 850),
             storm_wall=(1100, 950), oppy_dark=(1400, 950), breeze=(1300, 1000), dark_energy=(1200, 1000), dust_devil=(1300, 950),
             night_sit=(1250, 900), phobos_sky=(1280, 950), quake_bed=(1100, 950), jezero=(1280, 950), mystery=(1280, 950),
             rover_drive=(1000, 950), curvature=(1300, 800), birthday=(1280, 950), seasons=(1280, 700), heavy_return=(1100, 950),
             grass_breath=(1280, 1050), blue_sky=(1280, 1050), final_ticket=(1050, 1000), wipes=(1250, 900), fan_device=(1300, 800),
             drink=(1150, 900), touchdown=(1280, 950), small_room2=(1300, 900), mars_pad=(1300, 950), sleep_bag=(1250, 700),
             launch=(1280, 800), cabin_seat=(1100, 950), moons_fast=(1600, 800), journey_map=(1280, 700), first_leaf=(1000, 850))


class R:
    def __init__(self):
        self.T = json.load(open(ROOT / 'timeline.json'))
        self.mouth = np.load(ROOT / 'mouth.npy')
        self.moves = ['in', 'right', 'static', 'out', 'left', 'in', 'static', 'out']
        for k, s in enumerate(self.T['shots']):
            s['move'] = s['kw'].get('cam', self.moves[k % len(self.moves)])

    def shot_at(self, t):
        for s in self.T['shots']:
            if s['start'] <= t < s['end']:
                return s
        return self.T['shots'][-1]

    def frame(self, t):
        s = self.shot_at(t)
        surf, c = surface()
        p = ease((t - s['start']) / max(s['end'] - s['start'], 0.1))
        lt, d = t - s['base'], s['bend'] - s['base']
        c.save()
        mv = s['move']
        z, dx = 1.0, 0.0
        if mv == 'in':
            z = 1.0 + 0.05 * p
        elif mv == 'out':
            z = 1.05 - 0.05 * p
        elif mv == 'left':
            z, dx = 1.04, 45 - 90 * p
        elif mv == 'right':
            z, dx = 1.04, -45 + 90 * p
        fx, fy = FOCUS.get(s['name'], (W / 2, H * 0.55))
        z0 = {'wide': 1.0, 'close': 1.28, 'wide2': 1.1}[s.get('frame', 'wide')]
        if z0 == 1.0:
            fx, fy = W / 2, H / 2
        zz = z0 * z
        cx = min(max(fx - dx / zz, W / (2 * zz)), W - W / (2 * zz)); cy = min(max(fy, H / (2 * zz)), H - H / (2 * zz))
        c.translate(W / 2, H / 2); c.scale(zz, zz); c.translate(-cx, -cy)
        kw = {k: v for k, v in s['kw'].items() if k != 'cam'}
        getattr(shots, s['name'])(c, lt, d, **kw)
        c.restore()
        g = cairo.LinearGradient(0, 980, 0, H)
        g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.5)
        c.rectangle(0, 980, W, H - 980); c.set_source(g); c.fill()
        # bölüm adı
        for ch in self.T['chapters']:
            if ch['start'] - 0.05 <= t < ch['end'] + 0.1:
                a = min(fin(t, ch['start'] + 0.1, 0.4), 1 - fin(t, ch['end'] - 0.25, 0.3))
                x = round(W * 0.06)
                label(c, f"{ch['sec']}. bölüm", x, 1035, 'small', M, 'l', a, dy=12)
                label(c, ch['title'], x, 1110, 'chap', L, 'l', a, dy=12)
                c.set_line_width(3); col(c, M, a); c.move_to(x, 1172); c.line_to(x + 140 * a, 1172); c.stroke()
        # altyazı
        for sb in self.T['subs']:
            if sb['s'] <= t < sb['e']:
                a = min(fin(t, sb['s'], 0.12), 1 - fin(t, sb['e'] - 0.1, 0.1))
                label(c, sb['t'], W / 2, 1268, 'sub', L, 'c', a)
                break
        # avatar
        i = min(len(self.mouth) - 1, int(t * FPS))
        lv = float(self.mouth[i])
        avatar(c, 150, 1290, 68, mouth=max(0.0, (lv - 0.12) * 1.1), blink=shots.blink_at(t, 4.1, 0.7))
        surf.flush()
        return surf


def render_part(i, n):
    T = json.load(open(ROOT / 'timeline.json'))
    nf = int(T['total'] * FPS)
    a, b = nf * i // n, nf * (i + 1) // n
    r = R()
    out = ROOT / f'part{i}.mp4'
    vf = 'eq=saturation=0.93,vignette=angle=0.42,noise=alls=3:allf=t,format=yuv420p'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-threads', '1', str(out)], stdin=subprocess.PIPE)
    import time
    t0 = time.time()
    for f in range(a, b):
        s = r.frame(f / FPS)
        ff.stdin.write(bytes(s.get_data()))
        if (f - a) % 600 == 0:
            print(f'part{i} {f - a}/{b - a} {time.time() - t0:.0f}s', flush=True)
    ff.stdin.close(); ff.wait()
    print(f'part{i} bitti', flush=True)


def concat(n):
    lst = ROOT / 'parts.txt'
    lst.write_text(''.join(f"file 'part{i}.mp4'\n" for i in range(n)))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-i', str(ROOT / 'mix.m4a'),
                    '-map', '0:v', '-map', '1:a', '-c', 'copy', '-movflags', '+faststart', '-shortest', str(ROOT / 'video.mp4')], check=True)
    print('video tamam')


if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'timeline':
        build_timeline()
    elif m == 'audio':
        build_audio()
    elif m == 'frames':
        r = R()
        for x in sys.argv[2].split(','):
            s = r.frame(float(x)); to_pil(s).save(ROOT / f'test/f_{float(x):07.2f}.jpg', quality=88)
    elif m == 'part':
        render_part(int(sys.argv[2]), int(sys.argv[3]))
    elif m == 'speed':
        import time
        r = R(); t0 = time.time()
        for k in range(60):
            s = r.frame(100 + k / 30); b = bytes(s.get_data())
        print('kare/sn', 60 / (time.time() - t0))
    elif m == 'concat':
        concat(int(sys.argv[2]))
