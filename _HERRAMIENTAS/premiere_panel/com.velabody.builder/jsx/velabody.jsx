/* VELABODY Builder — arma la secuencia en Premiere a partir de _EDICION/armado.json
   (generado por _HERRAMIENTAS/velabody.py). ExtendScript (ES3): sin let/const/arrow. */

var VB = { log: [] };
var VB_VERSION = "2.1";

function vb_version() { return VB_VERSION; }
var TICKS = 254016000000;

/* cada paso queda también en _EDICION/construir_log.txt (si Premiere se cierra, se sabe dónde) */
function vbLog(t) {
    VB.log.push(t);
    if (!VB.archivo) return;
    var f = new File(VB.archivo);
    f.encoding = "UTF-8";
    f.open("a"); f.writeln(new Date().toTimeString().substr(0, 8) + "  " + t); f.close();
}

function leerJSON(ruta) {
    var f = new File(ruta);
    f.encoding = "UTF-8";
    if (!f.open("r")) throw new Error("No puedo abrir " + ruta);
    var txt = f.read();
    f.close();
    return eval("(" + txt + ")");
}

function aJSON(o) {
    if (o === null || o === undefined) return "null";
    var t = typeof o;
    if (t === "number" || t === "boolean") return String(o);
    if (t === "string") return '"' + o.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n").replace(/\r/g, "\\r") + '"';
    if (o instanceof Array) {
        var a = [];
        for (var i = 0; i < o.length; i++) a.push(aJSON(o[i]));
        return "[" + a.join(",") + "]";
    }
    var p = [];
    for (var k in o) if (o.hasOwnProperty(k)) p.push(aJSON(k) + ":" + aJSON(o[k]));
    return "{" + p.join(",") + "}";
}

/* clave de comparación de rutas: solo ASCII (Premiere y el JSON pueden diferir en "—", "·", acentos) */
function norm(r) { return String(r).replace(/\//g, "\\").toLowerCase().replace(/[^ -~]/g, ""); }

function tiempo(seg) { var t = new Time(); t.seconds = seg; return t; }
function ticks(seg) { return String(Math.round(seg * TICKS)); }

/* ---------------------------------------------------------------- proyecto */

function buscarBin(padre, nombre) {
    for (var i = 0; i < padre.children.numItems; i++) {
        var c = padre.children[i];
        if (c.type === ProjectItemType.BIN && c.name === nombre) return c;
    }
    return padre.createBin(nombre);
}

function recorrer(item, fn) {
    for (var i = 0; i < item.children.numItems; i++) {
        var c = item.children[i];
        if (c.type === ProjectItemType.BIN) {
            var hallado = recorrer(c, fn);
            if (hallado) return hallado;
        } else if (fn(c)) return c;
    }
    return null;
}

function itemPorRuta(ruta) {
    var n = norm(ruta);
    return recorrer(app.project.rootItem, function (c) {
        try { return c.getMediaPath && norm(c.getMediaPath()) === n; } catch (e) { return false; }
    });
}

function itemPorNombre(nombre) {
    return recorrer(app.project.rootItem, function (c) { return c.name === nombre; });
}

function importar(rutas, bin) {
    var faltan = [];
    for (var i = 0; i < rutas.length; i++) {
        if (!rutas[i]) continue;
        if (!new File(rutas[i]).exists) { vbLog("⚠ No existe: " + rutas[i]); continue; }
        if (!itemPorRuta(rutas[i])) faltan.push(rutas[i]);
    }
    if (faltan.length) app.project.importFiles(faltan, true, bin, false);
    var mapa = {};
    for (var j = 0; j < rutas.length; j++) if (rutas[j]) mapa[norm(rutas[j])] = itemPorRuta(rutas[j]);
    return mapa;
}

/* -------------------------------------------------------------- secuencia */

function crearSecuencia(a, bin, primerItem) {
    var nombre = a.nombre;
    var tpl = null;
    for (var i = 0; i < app.project.sequences.numSequences; i++)
        if (app.project.sequences[i].name === a.recursos.plantilla_secuencia_nombre) tpl = app.project.sequences[i];
    var seq;
    if (tpl) {
        // la copia se reconoce por su ID nuevo (la lista está ordenada por ID, no por creación)
        var ids = {};
        for (var s0 = 0; s0 < app.project.sequences.numSequences; s0++) ids[app.project.sequences[s0].sequenceID] = true;
        tpl.clone();
        seq = null;
        for (var s1 = 0; s1 < app.project.sequences.numSequences; s1++)
            if (!ids[app.project.sequences[s1].sequenceID]) seq = app.project.sequences[s1];
        if (!seq) throw new Error("No pude duplicar la plantilla");
        seq.name = nombre;
        seq.projectItem.moveBin(bin);
        vbLog("Secuencia creada desde la plantilla " + tpl.name);
    } else {
        seq = app.project.createNewSequenceFromClips(nombre, [primerItem], bin);
        // vaciar lo que insertó y ajustar formato vertical
        for (var v = 0; v < seq.videoTracks.numTracks; v++)
            for (var k = seq.videoTracks[v].clips.numItems - 1; k >= 0; k--) seq.videoTracks[v].clips[k].remove(false, false);
        for (var au = 0; au < seq.audioTracks.numTracks; au++)
            for (var k2 = seq.audioTracks[au].clips.numItems - 1; k2 >= 0; k2--) seq.audioTracks[au].clips[k2].remove(false, false);
        var s = seq.getSettings();
        s.videoFrameWidth = a.secuencia.ancho;
        s.videoFrameHeight = a.secuencia.alto;
        var fr = new Time(); fr.ticks = String(TICKS / a.secuencia.fps);
        s.videoFrameRate = fr;
        seq.setSettings(s);
        vbLog("Secuencia nueva " + a.secuencia.ancho + "x" + a.secuencia.alto + " @" + a.secuencia.fps);
    }
    app.project.openSequence(seq.sequenceID);
    app.project.activeSequence = seq;
    asegurarPistas(seq, 6, 5);
    return seq;
}

function asegurarPistas(seq, nV, nA) {
    var faltanV = Math.max(0, nV - seq.videoTracks.numTracks);
    var faltanA = Math.max(0, nA - seq.audioTracks.numTracks);
    if (!faltanV && !faltanA) return;
    app.enableQE();
    var qs = qe.project.getActiveSequence();
    qs.addTracks(faltanV, seq.videoTracks.numTracks, faltanA, 1, seq.audioTracks.numTracks, 0, 1, 0);
}

function clipEn(track, seg, nombre) {
    var mejor = null, d = 1e9;
    for (var i = 0; i < track.clips.numItems; i++) {
        var c = track.clips[i];
        var dd = Math.abs(c.start.seconds - seg);
        if (dd < d && (!nombre || c.name === nombre)) { d = dd; mejor = c; }
    }
    return d < 0.1 ? mejor : null;
}

function poner(track, item, t, ini, fin) {
    if (ini !== undefined) {
        item.setInPoint(ini, 4);
        item.setOutPoint(fin, 4);
    }
    track.overwriteClip(item, t);
    if (ini !== undefined) { item.clearInPoint(4); item.clearOutPoint(4); }
    return clipEn(track, t, item.name);
}

function prop(componente, nombre) {
    for (var i = 0; i < componente.properties.numItems; i++)
        if (componente.properties[i].displayName === nombre) return componente.properties[i];
    return null;
}

function componente(trackItem, matchName, nombre) {
    for (var i = 0; i < trackItem.components.numItems; i++) {
        var c = trackItem.components[i];
        if (c.matchName === matchName || c.displayName === nombre) return c;
    }
    return null;
}

/* escala y encuadre 9:16 (foco_x / foco_y = punto del cuadro original que queda al centro, 0..1;
   zoom > 1 = plano más cercano) */
function encuadrar(ti, medio, a, focoX, zoom, focoY) {
    var W = a.secuencia.ancho, H = a.secuencia.alto;
    var esc = Math.max(W / medio.ancho, H / medio.alto) * (zoom || 1);
    var anchoEsc = medio.ancho * esc, altoEsc = medio.alto * esc;
    var centro = W / 2 + (0.5 - (focoX === undefined ? 0.5 : focoX)) * anchoEsc;
    var maxDesp = (anchoEsc - W) / 2;
    centro = Math.max(W / 2 - maxDesp, Math.min(W / 2 + maxDesp, centro));
    var centroY = H / 2 + (0.5 - (focoY === undefined ? 0.5 : focoY)) * altoEsc;
    var maxDespY = (altoEsc - H) / 2;
    centroY = Math.max(H / 2 - maxDespY, Math.min(H / 2 + maxDespY, centroY));
    var mov = componente(ti, "AE.ADBE Motion", "Movimiento");
    if (!mov) return;
    var pEsc = prop(mov, "Escala") || prop(mov, "Scale");
    var pPos = prop(mov, "Posición") || prop(mov, "Position");
    if (pEsc) pEsc.setValue(esc * 100, true);
    if (pPos) pPos.setValue([centro / W, centroY / H], true);
}

function volumen(ti, db) {
    var c = componente(ti, "AE.ADBE Volume", "Volumen") || ti.components[0];
    var p = prop(c, "Nivel") || prop(c, "Level");
    if (p) p.setValue(Math.pow(10, (db - 15) / 20), true);
}

function quitarAudioVinculado(seq, idxAudio, t, nombre) {
    var c = clipEn(seq.audioTracks[idxAudio], t, nombre);
    if (c) c.remove(false, false);
}

/* ----------------------------------------------------------------- títulos */

function colorHex(h) {
    return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)];
}

function ponerTexto(p, pieza, factor) {
    var v = p.getValue();
    var o;
    try { o = eval("(" + v + ")"); } catch (e) { o = null; }
    if (o && o.textEditValue !== undefined) {
        o.textEditValue = pieza.texto;
        o.fontEditValue = [pieza.fuente];
        o.fontSizeEditValue = [pieza.tamano * factor];
        o.fontFSItalicValue = [pieza.italica];
        o.fontTextRunLength = [pieza.texto.length];
        o.capPropFontEdit = true;
        o.capPropFontSizeEdit = true;
        o.capPropFontFauxStyleEdit = true;
        p.setValue(aJSON(o), true);
    } else {
        p.setValue(pieza.texto, true);
    }
}

/* Los MOGRT de Mister Horse son comps de 1920x1080: Premiere los centra al 100 % en la secuencia
   vertical y lo que cae fuera de la comp (arriba de y≈420) se recorta. Por eso:
   - el clip entero se mueve con Movimiento > Posición hasta el centro vertical del título;
   - adentro de la comp, la posición es relativa a ese centro (u, v normalizados a la comp).
   El texto del MOGRT de texto se ancla en la línea de base; la pastilla, en su centro. */
function posMogrt(pz, yCentroTitulo, a) {
    var cw = a.mogrt_comp[0], ch = a.mogrt_comp[1];
    var yAncla = pz.estilo === "pastilla" ? pz.y : pz.y + pz.alto_mayus / 2;
    return [0.5 + (pz.x - a.secuencia.ancho / 2) / cw, 0.5 + (yAncla - yCentroTitulo) / ch];
}

function ponerTitulos(seq, a, op, mapa) {
    var violeta = colorHex(a.violeta);
    var pista = 4; // V5
    for (var i = 0; i < a.titulos.length; i++) {
        var ti = a.titulos[i];
        var yc = ti.caja[1] + ti.caja[3] / 2;
        for (var k = 0; k < ti.piezas.length; k++) {
            var pz = ti.piezas[k];
            var mogrt = pz.estilo === "pastilla" ? a.recursos.mogrt_pastilla : a.recursos.mogrt_texto;
            // cada pieza en su pista (V5, V6…) para que no se pisen
            var vIdx = pista + k;
            asegurarPistas(seq, vIdx + 2, 5);
            var item = seq.importMGT(mogrt, ticks(ti.t + k * 0.08), vIdx, 4);
            if (!item) { vbLog("⚠ No pude insertar el MOGRT " + mogrt); continue; }
            item.end = tiempo(ti.t + ti.dur);
            // el clip completo baja/sube hasta el centro del título
            var mov = componente(item, "AE.ADBE Motion", "Movimiento");
            var pMov = mov ? (prop(mov, "Posición") || prop(mov, "Position")) : null;
            if (pMov) pMov.setValue([0.5, yc / a.secuencia.alto], true);
            var mgt = item.getMGTComponent();
            var redondeo = ((pz.alto_mayus || 0) + 2 * (pz.padding ? pz.padding[1] : 0)) * 0.45;
            for (var j = 0; j < mgt.properties.numItems; j++) {
                var p = mgt.properties[j];
                var dn = p.displayName;
                var val; try { val = p.getValue(); } catch (e) { val = null; }
                if (typeof val === "string" && (dn === "Text" || dn === "Texto")) ponerTexto(p, pz, op.factor);
                else if (dn === "Position" || dn === "Posición") p.setValue(posMogrt(pz, yc, a), true);
                else if (pz.estilo === "pastilla") {
                    if (dn === "Container Fill") p.setColorValue(255, violeta[0], violeta[1], violeta[2], true);
                    else if (dn === "Text" && typeof val !== "string") p.setColorValue(255, 255, 255, 255, true);
                    else if (dn === "Round Corners") p.setValue(redondeo, true);
                    else if (dn === "Horizontal Padding") p.setValue(pz.padding_mogrt[0], true);
                    else if (dn === "Vertical Padding") p.setValue(pz.padding_mogrt[1], true);
                } else if (dn === "Color Fill") p.setColorValue(255, violeta[0], violeta[1], violeta[2], true);
            }
        }
        // click en cada título (A2)
        var click = mapa[norm(a.recursos.click)];
        if (click) { var c = poner(seq.audioTracks[1], click, ti.t); if (c) volumen(c, a.audio.click_db); }
        var m = seq.markers.createMarker(ti.t);
        m.name = "TÍTULO";
    }
    vbLog("Títulos: " + a.titulos.length);
}

/* ------------------------------------------------------- estilo v2 (28/10) */

/* La secuencia se arma sobre una copia de la del Video 1 cerrado: de ahí salen la capa de ajuste con
   el Lumetri (LUT Alexa, exposición 0,4, contraste 65) y las transiciones Pan Left de Mister Horse
   (dos "Gráfico" por pista, en dos pistas), que por script no se pueden crear. Se mueven a su lugar
   y todo lo demás se borra. */

function clipsDe(track) { var r = []; for (var i = 0; i < track.clips.numItems; i++) r.push(track.clips[i]); return r; }

function fijarMovimiento(ti, a, escala, pos, kf) {
    var mov = componente(ti, "AE.ADBE Motion", "Movimiento");
    if (!mov) return;
    var pEsc = prop(mov, "Escala") || prop(mov, "Scale");
    var pPos = prop(mov, "Posición") || prop(mov, "Position");
    var W = a.secuencia.ancho, H = a.secuencia.alto;
    if (!kf) {
        if (pEsc) pEsc.setValue(escala, true);
        if (pPos) pPos.setValue([pos[0] / W, pos[1] / H], true);
        return;
    }
    // zoom in con dos keyframes lineales; el tiempo de la clave es el del medio (punto de entrada + offset)
    var base = ti.inPoint.seconds - ti.start.seconds;
    var props = [[pEsc, function (k) { return k.escala; }], [pPos, function (k) { return [k.pos[0] / W, k.pos[1] / H]; }]];
    for (var p = 0; p < props.length; p++) {
        var pr = props[p][0];
        if (!pr) continue;
        pr.setTimeVarying(true);
        for (var k = 0; k < kf.length; k++) {
            var tk = tiempo(base + kf[k].t);
            pr.addKey(tk);
            pr.setValueAtKey(tk, props[p][1](kf[k]), true);
            pr.setInterpolationTypeAtKey(tk, 0, true);
        }
    }
}

function ponerTextoV2(mgt, texto, fuente, tamano) {
    for (var j = 0; j < mgt.properties.numItems; j++) {
        var p = mgt.properties[j], v;
        try { v = p.getValue(); } catch (e) { continue; }
        if (typeof v !== "string") continue;
        var o; try { o = eval("(" + v + ")"); } catch (e2) { o = null; }
        if (!o || o.textEditValue === undefined) continue;
        o.textEditValue = texto;
        o.fontEditValue = [fuente];
        o.fontSizeEditValue = [tamano];
        o.fontFSItalicValue = [false];
        o.fontFSAllCapsValue = [true];
        o.fontTextRunLength = [texto.length];
        o.capPropFontEdit = true;
        o.capPropFontSizeEdit = tamano !== 75;
        o.capPropFontFauxStyleEdit = true;
        p.setValue(aJSON(o), true);
        return true;
    }
    return false;
}

function construirV2(a, op, bin, mapa) {
    var e2 = a.estilo_v2, P = e2.pistas;
    var base = null;
    for (var s = 0; s < app.project.sequences.numSequences; s++)
        if (app.project.sequences[s].name === e2.secuencia_base) base = app.project.sequences[s];
    if (!base) throw new Error("No encuentro la secuencia base " + e2.secuencia_base);
    // Premiere ordena app.project.sequences por ID, no por creación: la copia se reconoce porque su
    // ID no existía antes (tomar "la última" de la lista pisó una secuencia ajena el 29/10)
    var ids = {};
    for (var s0 = 0; s0 < app.project.sequences.numSequences; s0++) ids[app.project.sequences[s0].sequenceID] = true;
    base.clone();
    var seq = null;
    for (var s1 = 0; s1 < app.project.sequences.numSequences; s1++)
        if (!ids[app.project.sequences[s1].sequenceID]) seq = app.project.sequences[s1];
    if (!seq) throw new Error("No pude duplicar la secuencia base");
    if (seq.name.indexOf(e2.secuencia_base) !== 0) throw new Error("La secuencia nueva no es copia de la base: " + seq.name);
    // nombre del brief + _H1/_H2… y adentro de la bandeja del video (Juli 30/10)
    for (var s2 = 0; s2 < app.project.sequences.numSequences; s2++)
        if (app.project.sequences[s2].name === a.nombre && app.project.sequences[s2].sequenceID !== seq.sequenceID)
            vbLog("⚠ Ya había una secuencia \"" + a.nombre + "\": quedan dos con el mismo nombre (borrar la vieja)");
    seq.name = a.nombre;
    seq.projectItem.moveBin(bin);
    app.project.openSequence(seq.sequenceID);
    app.project.activeSequence = seq;
    vbLog("Secuencia " + seq.name + " (copia de " + base.name + ")");

    // inventario: transiciones Pan Left (por corte) y capas de ajuste con Lumetri en la pista de ajuste
    var grupos = [], ajustes = [], guardar = [];
    for (var v = 0; v < seq.videoTracks.numTracks; v++) {
        var cs = clipsDe(seq.videoTracks[v]);
        for (var c = 0; c < cs.length; c++) {
            var ti = cs[c];
            if (ti.name === "Gráfico") {
                var dur = ti.end.seconds - ti.start.seconds;
                var corte = dur < 0.25 ? ti.end.seconds : ti.start.seconds;
                var g = null;
                for (var k = 0; k < grupos.length; k++) if (Math.abs(grupos[k].corte - corte) < 0.05) g = grupos[k];
                if (!g) { g = { corte: corte, items: [] }; grupos.push(g); }
                g.items.push(ti);
            } else if (v === P.ajuste - 1 && ti.name === "Capa de ajuste" && componente(ti, "AE.ADBE Lumetri", "Color de Lumetri")) {
                ajustes.push(ti);
            }
        }
    }
    vbLog("Base: " + grupos.length + " Pan Left, " + ajustes.length + " capas de ajuste con Lumetri");
    // se usan primero las del medio (no chocan al moverse); la del arranque del Video 1 queda de reserva
    grupos.sort(function (x, y) { return (x.corte < 1.6) - (y.corte < 1.6) || x.corte - y.corte; });
    var usar = grupos.slice(0, a.transiciones.length);
    if (usar.length < a.transiciones.length) vbLog("⚠ Hay " + a.transiciones.length + " transiciones y la base trae " + usar.length);
    for (var u = 0; u < usar.length; u++) for (var q = 0; q < usar[u].items.length; q++) guardar.push(usar[u].items[q]);
    ajustes.sort(function (x, y) { return x.start.seconds - y.start.seconds; });
    if (ajustes.length) guardar.push(ajustes[0]);

    // borrar todo lo demás (video, audio y marcadores)
    var esGuardado = function (ti) { for (var i = 0; i < guardar.length; i++) if (guardar[i].nodeId === ti.nodeId) return true; return false; };
    for (var vv = 0; vv < seq.videoTracks.numTracks; vv++) {
        var lista = clipsDe(seq.videoTracks[vv]);
        for (var r = lista.length - 1; r >= 0; r--) if (!esGuardado(lista[r])) lista[r].remove(false, false);
    }
    for (var aa = 0; aa < seq.audioTracks.numTracks; aa++) {
        var la = clipsDe(seq.audioTracks[aa]);
        for (var r2 = la.length - 1; r2 >= 0; r2--) la[r2].remove(false, false);
    }
    var mk = seq.markers.getFirstMarker();
    while (mk) { var sig = seq.markers.getNextMarker(mk); seq.markers.deleteMarker(mk); mk = sig; }

    // Lumetri: una capa de ajuste estirada a todo el video
    if (ajustes.length) {
        var aj = ajustes[0];
        aj.move(tiempo(-aj.start.seconds));
        aj.end = tiempo(a.duracion);
        vbLog("Lumetri: capa de ajuste 0 – " + aj.end.seconds.toFixed(2) + " s (video " + a.duracion.toFixed(2) + " s)");
        if (aj.end.seconds < a.duracion - 0.05) vbLog("⚠ La capa de ajuste no alcanza: estirarla a mano hasta el final");
    } else vbLog("⚠ La base no tiene capa de ajuste con Lumetri");

    // transiciones: primero las que van hacia atrás (en orden), después las que van hacia adelante (al revés)
    var destinos = a.transiciones.slice(0).sort(function (x, y) { return x.t - y.t; });
    var pares = [];
    usar.sort(function (x, y) { return x.corte - y.corte; });
    for (var d = 0; d < usar.length; d++) pares.push({ g: usar[d], t: destinos[d].t });
    var izq = [], der = [];
    for (var pp = 0; pp < pares.length; pp++) (pares[pp].t < pares[pp].g.corte ? izq : der).push(pares[pp]);
    der.reverse();
    var orden = izq.concat(der);
    for (var o2 = 0; o2 < orden.length; o2++) {
        var delta = orden[o2].t - orden[o2].g.corte;
        for (var it2 = 0; it2 < orden[o2].g.items.length; it2++) orden[o2].g.items[it2].move(tiempo(delta));
    }
    var donde = [];
    for (var dd = 0; dd < pares.length; dd++) donde.push(pares[dd].t.toFixed(2) + " s");
    vbLog("Pan Left: " + pares.length + " (" + donde.join(", ") + ")");

    // A-roll (V1/A1) con encuadre, zooms y voz
    for (var i = 0; i < a.aroll.length; i++) {
        var x = a.aroll[i], itm = mapa[norm(a.medios[x.clip].ruta)];
        var finTl = tiempo(x.t + (x.out - x["in"]));
        if (x.solo_audio) {
            // voz en off: solo audio en la pista de voz (la imagen la cubren los inserts)
            var vo = poner(seq.audioTracks[P.a_voz - 1], itm, x.t, x["in"], x.out);
            if (vo) { volumen(vo, x.ganancia_db); vo.end = finTl; }
            continue;
        }
        var vclip = poner(seq.videoTracks[P.aroll - 1], itm, x.t, x["in"], x.out);
        if (vclip) { vclip.end = finTl; fijarMovimiento(vclip, a, x.escala, x.pos, x.kf); }
        var au = clipEn(seq.audioTracks[P.a_voz - 1], x.t, itm.name);
        if (au) { volumen(au, x.ganancia_db); au.end = finTl; }
    }
    vbLog("A-roll: " + a.aroll.length + " cortes");

    // B-roll (V3) sin audio
    for (var b = 0; b < a.broll.length; b++) {
        var y = a.broll[b], itb = mapa[norm(a.medios[y.clip].ruta)];
        var vb = poner(seq.videoTracks[P.broll - 1], itb, y.t, y["in"], y.out);
        if (vb) { encuadrar(vb, a.medios[y.clip], a, y.foco_x, y.zoom, y.foco_y); vb.end = tiempo(y.t + (y.out - y["in"])); }
        quitarAudioVinculado(seq, P.broll - 1, y.t, itb.name);
    }
    vbLog("B-roll: " + a.broll.length + " clips");

    // SFX de cada transición (A2), un poco antes del corte
    var sfx = mapa[norm(e2.sfx_transicion)];
    for (var tr = 0; tr < a.transiciones.length && sfx; tr++) {
        var cs2 = poner(seq.audioTracks[P.a_sfx - 1], sfx, Math.max(0, a.transiciones[tr].t - e2.sfx_adelanto));
        if (cs2) volumen(cs2, e2.sfx_transicion_db);
    }

    // música (A3) con fundido al final
    if (a.musica) {
        var mu = poner(seq.audioTracks[P.a_musica - 1], mapa[norm(a.musica.ruta)], 0);
        if (mu) {
            mu.end = tiempo(a.duracion);
            volumen(mu, a.musica.db);
            if (!a.solo_hook) {
                var nivel = prop(componente(mu, "AE.ADBE Volume", "Volumen") || mu.components[0], "Nivel");
                if (nivel) {
                    var t0 = tiempo(Math.max(0, a.duracion - e2.musica_fade)), t1 = tiempo(a.duracion);
                    nivel.setTimeVarying(true);
                    nivel.addKey(t0); nivel.setValueAtKey(t0, Math.pow(10, (a.musica.db - 15) / 20), true);
                    nivel.addKey(t1); nivel.setValueAtKey(t1, 0, true);
                }
            }
        }
        vbLog("Música a " + a.musica.db + " dB");
    }

    // títulos y pastillas (V5–V7) + click (A4)
    if (op.titulos) {
        var mTit = itemPorNombre(e2.mogrt_titulo), mPas = itemPorNombre(e2.mogrt_pastilla);
        if (!mTit || !mPas) vbLog("⚠ Falta en el proyecto: " + (!mTit ? e2.mogrt_titulo : e2.mogrt_pastilla));
        var violeta = colorHex(a.violeta), ocupado = {};
        var click = mapa[norm(a.recursos.click)];
        for (var gi = 0; gi < a.graficos.length; gi++) {
            var gr = a.graficos[gi], fuente = gr.tipo === "pastilla" ? mPas : mTit;
            if (!fuente) continue;
            var pista = null;
            for (var pi = 0; pi < P.graficos.length; pi++) {
                var n = P.graficos[pi];
                if (!ocupado[n] || ocupado[n] <= gr.t + 0.01) { pista = n; break; }
            }
            if (!pista) { vbLog("⚠ Sin pista libre para " + gr.texto); continue; }
            ocupado[pista] = gr.fin;
            var tiG = poner(seq.videoTracks[pista - 1], fuente, gr.t);
            if (!tiG) { vbLog("⚠ No pude poner " + gr.texto); continue; }
            tiG.end = tiempo(gr.fin);
            fijarMovimiento(tiG, a, gr.escala, gr.pos);
            var mgt = tiG.getMGTComponent();
            if (mgt) {
                // pastilla como en el Video 1: ExtraBold a 75 (el tamaño que trae), Scale 285, esquinas 140
                var esPas = gr.tipo === "pastilla";
                if (!ponerTextoV2(mgt, gr.texto, esPas ? "Montserrat-ExtraBold" : "Montserrat-Medium", esPas ? 75 : 100))
                    vbLog("⚠ No encontré el campo de texto de " + gr.texto);
                for (var j = 0; j < mgt.properties.numItems; j++) {
                    var pm = mgt.properties[j], dn = pm.displayName, val;
                    try { val = pm.getValue(); } catch (e3) { continue; }
                    if (typeof val === "string") continue;
                    if (gr.tipo === "pastilla") {
                        if (dn === "Container Fill") pm.setColorValue(255, violeta[0], violeta[1], violeta[2], true);
                        else if (dn === "Text") pm.setColorValue(255, 255, 255, 255, true);
                        else if (dn === "Scale") pm.setValue(285, true);
                        else if (dn === "Round Corners") pm.setValue(139.97, true);
                    } else if (dn === "Color Fill") pm.setColorValue(255, violeta[0], violeta[1], violeta[2], true);
                }
            }
            if (click) { var ck = poner(seq.audioTracks[P.a_click - 1], click, gr.t); if (ck) volumen(ck, a.audio.click_db); }
        }
        vbLog("Gráficos: " + a.graficos.length);
    }

    // guía de zona segura, desactivada
    var zs = mapa[norm(a.recursos.zona_segura)];
    if (zs) {
        var vz = poner(seq.videoTracks[P.zona_segura - 1], zs, 0);
        if (vz) { vz.end = tiempo(a.duracion); vz.disabled = true; }
    }

    // subtítulos: dos pistas (a cámara / B-roll)
    if (op.subs) {
        // un .srt vacío (hook solo, sin B-roll) frena a Premiere con "Error al importar archivo"
        var conTexto = [];
        if (new File(a.subtitulos.camara).length > 0) conTexto.push(a.subtitulos.camara);
        if (new File(a.subtitulos.broll).length > 0) conTexto.push(a.subtitulos.broll);
        var srt = importar(conTexto, bin);
        var fmt = Sequence.CAPTION_FORMAT_SUBTITLE;
        var s1 = srt[norm(a.subtitulos.camara)], s2 = srt[norm(a.subtitulos.broll)];
        if (s1) seq.createCaptionTrack(s1, 0, fmt);
        if (s2) seq.createCaptionTrack(s2, 0, fmt);
        vbLog("Subtítulos: 2 pistas (aplicá los estilos de pista de los subtítulos del Video 1)");
    }
    vbLog("✔ Listo: " + seq.name);
    return seq;
}

/* --------------------------------------------------------------- construir */

function vb_construir(rutaArmado, opcionesJSON) {
    VB.log = [];
    VB.archivo = new File(rutaArmado).parent.fsName + "/construir_log.txt";
    try {
        vbLog("— Construir: " + rutaArmado);
        var op = eval("(" + opcionesJSON + ")");
        var a = leerJSON(rutaArmado);
        // una bandeja por video con el nombre del brief (armados viejos: una por pieza)
        var bin = buscarBin(app.project.rootItem, a.bandeja || ("VELABODY · " + a.nombre));
        if (a.estilo_v2) {
            var rutasV2 = [];
            for (var k2 in a.medios) if (a.medios.hasOwnProperty(k2)) rutasV2.push(a.medios[k2].ruta);
            rutasV2.push(a.recursos.click, a.recursos.zona_segura, a.estilo_v2.sfx_transicion);
            vbLog("Importando " + rutasV2.length + " archivos…");
            construirV2(a, op, bin, importar(rutasV2, bin));
            return VB.log.join("\n");
        }

        var rutas = [];
        for (var k in a.medios) if (a.medios.hasOwnProperty(k)) rutas.push(a.medios[k].ruta);
        rutas.push(a.recursos.click, a.recursos.zona_segura);
        for (var l = 0; l < a.light_leaks.length; l++) rutas.push(a.light_leaks[l].sfx);
        vbLog("Importando " + rutas.length + " archivos…");
        var mapa = importar(rutas, bin);
        vbLog("Importación OK");
        var porClip = function (nombre) { return mapa[norm(a.medios[nombre].ruta)]; };

        vbLog("Creando secuencia…");
        var seq = crearSecuencia(a, bin, porClip(a.aroll[0].clip));

        // V1/A1 — A-roll
        for (var i = 0; i < a.aroll.length; i++) {
            var x = a.aroll[i], it = porClip(x.clip);
            if (x.solo_audio) {
                // voz en off: solo audio en A1 (el video del bloque lo cubren los inserts en V2)
                var vo = poner(seq.audioTracks[0], it, x.t, x["in"], x.out);
                if (vo) { volumen(vo, x.ganancia_db); vo.end = tiempo(x.t + (x.out - x["in"])); }
                continue;
            }
            var v = poner(seq.videoTracks[0], it, x.t, x["in"], x.out);
            // el in/out se redondea al cuadro del original (25/50 fps) y el clip puede quedar un cuadro
            // corto en la secuencia de 30 fps: se fuerza el final exacto para no dejar cuadros negros
            var finTl = tiempo(x.t + (x.out - x["in"]));
            if (v) { encuadrar(v, a.medios[x.clip], a, x.foco_x, x.zoom, x.foco_y); v.end = finTl; }
            var au = clipEn(seq.audioTracks[0], x.t, it.name);
            if (au) { volumen(au, x.ganancia_db); au.end = finTl; }
        }
        vbLog("A-roll: " + a.aroll.length + " cortes");

        // V2 — B-roll (sin audio)
        for (var b = 0; b < a.broll.length; b++) {
            var y = a.broll[b], itb = porClip(y.clip);
            var vb = poner(seq.videoTracks[1], itb, y.t, y["in"], y.out);
            if (vb) { encuadrar(vb, a.medios[y.clip], a, y.foco_x, y.zoom, y.foco_y); vb.end = tiempo(y.t + (y.out - y["in"])); }
            quitarAudioVinculado(seq, 1, y.t, itb.name);
        }
        vbLog("B-roll: " + a.broll.length + " clips");

        // V3 — capa de ajuste con Lumetri: si vino con la plantilla, se recorta al largo del video;
        // si no, se busca una capa de ajuste en el proyecto (sin efectos: Lumetri a mano)
        var ajustePlantilla = seq.videoTracks[2].clips.numItems ? seq.videoTracks[2].clips[0] : null;
        var ajuste = ajustePlantilla ? null : itemPorNombre(a.recursos.ajuste_lumetri_nombre);
        if (ajustePlantilla) {
            ajustePlantilla.end = tiempo(a.duracion);
            vbLog("Lumetri: capa de ajuste de la plantilla recortada a " + a.duracion.toFixed(1) + " s");
        } else if (ajuste) {
            var aj = poner(seq.videoTracks[2], ajuste, 0);
            if (aj) aj.end = tiempo(a.duracion);
            vbLog("Lumetri: capa de ajuste aplicada");
        } else vbLog("⚠ No hay capa de ajuste '" + a.recursos.ajuste_lumetri_nombre + "' en el proyecto (Lumetri a mano)");

        // V4 — light leaks (con alfa) + A3 SFX
        for (var j = 0; j < a.light_leaks.length; j++) {
            var lk = a.light_leaks[j], itl = mapa[norm(lk.ruta)];
            if (!itl) continue;
            var vl = poner(seq.videoTracks[3], itl, lk.t);
            // el .mov ya trae transparencia (ver leak_con_alfa en velabody.py): modo Normal
            if (vl) encuadrar(vl, a.medios[lk.ruta], a, 0.5, 1);
            quitarAudioVinculado(seq, 3, lk.t, itl.name);
            var sfx = mapa[norm(lk.sfx)];
            if (sfx) { var cs = poner(seq.audioTracks[2], sfx, Math.max(0, lk.t - 0.2)); if (cs) volumen(cs, a.audio.sfx_light_db); }
        }
        vbLog("Light leaks: " + a.light_leaks.length);

        // A4 — música
        if (a.musica) {
            var mu = poner(seq.audioTracks[3], mapa[norm(a.musica.ruta)], 0);
            if (mu) { mu.end = tiempo(a.duracion); volumen(mu, a.musica.db); }
            vbLog("Música a " + a.musica.db + " dB");
        }

        // títulos + clicks
        if (op.titulos) { vbLog("Insertando títulos…"); ponerTitulos(seq, a, op, mapa); }

        // guía de zona segura, desactivada, en la pista más alta
        var zs = mapa[norm(a.recursos.zona_segura)];
        if (zs) {
            var top = seq.videoTracks.numTracks;
            asegurarPistas(seq, top + 1, 5);
            var vz = poner(seq.videoTracks[top], zs, 0);
            if (vz) { vz.end = tiempo(a.duracion); vz.disabled = true; }
        }

        // subtítulos: dos pistas (a cámara / B-roll)
        if (op.subs) {
            var srt = importar([a.subtitulos.camara, a.subtitulos.broll], bin);
            var fmt = Sequence.CAPTION_FORMAT_SUBTITLE;
            var s1 = srt[norm(a.subtitulos.camara)], s2 = srt[norm(a.subtitulos.broll)];
            if (s1) seq.createCaptionTrack(s1, 0, fmt);
            if (s2) seq.createCaptionTrack(s2, 0, fmt);
            vbLog("Subtítulos: 2 pistas (aplicá los estilos 'VELABODY SUBS CAMARA' y 'VELABODY SUBS C FONDO')");
        }
        vbLog("✔ Listo: " + seq.name);
    } catch (e) {
        vbLog("✖ Error: " + e.message + (e.line ? " (línea " + e.line + ")" : ""));
    }
    return VB.log.join("\n");
}

/* ---------------------------------------------------------- elegir archivo */

function vb_elegirArmado(actual) {
    var inicio = new File(actual || "E:/VELABODY/armado.json");
    var f = inicio.openDlg("Elegir armado.json", "JSON:*.json", false);
    return f ? f.fsName : "";
}

/* ------------------------------------------------------------- diagnóstico */

function vb_diagnostico(rutaArmado) {
    var seq = app.project.activeSequence;
    if (!seq) return "No hay secuencia activa";
    var sel = seq.getSelection();
    var out = ["Diagnóstico " + new Date() + " — " + seq.name, ""];
    for (var i = 0; i < sel.length; i++) {
        var ti = sel[i];
        out.push("== " + ti.name + "  [" + ti.start.seconds.toFixed(2) + "–" + ti.end.seconds.toFixed(2) + "]");
        for (var c = 0; c < ti.components.numItems; c++) {
            var comp = ti.components[c];
            out.push("  # " + comp.displayName + "  (" + comp.matchName + ")");
            for (var p = 0; p < comp.properties.numItems; p++) {
                var pr = comp.properties[p], v;
                try { v = pr.getValue(); } catch (e) { v = "?"; }
                if (v instanceof Array) v = "[" + v.join(", ") + "]";
                out.push("     - " + pr.displayName + " = " + String(v).substr(0, 400));
            }
        }
    }
    var dir = rutaArmado ? new File(rutaArmado).parent.fsName : Folder.desktop.fsName;
    var f = new File(dir + "/diagnostico_premiere.txt");
    f.encoding = "UTF-8";
    f.open("w"); f.write(out.join("\n")); f.close();
    return "Diagnóstico de " + sel.length + " clips guardado en " + f.fsName;
}
