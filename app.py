import streamlit as st
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus import Image as RLImage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Laudo Psicossocial HSE-IT",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS customizado ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #1a3557 0%, #2e6da4 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p  { color: #a8c8e8; margin: 0.5rem 0 0; font-size: 0.95rem; }
    
    .section-header {
        background: #f8fafc;
        border-left: 4px solid #2e6da4;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1.5rem 0 1rem;
        font-weight: 600;
        color: #1a3557;
        font-size: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f0f4f8;
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        background: #1a3557 !important;
        color: white !important;
    }
    .score-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .alert-box {
        background: #fff8e1;
        border: 1px solid #f39c12;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.88rem;
        color: #7d4e00;
    }
    .info-box {
        background: #eaf4fb;
        border: 1px solid #2e6da4;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.88rem;
        color: #1a3557;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    div[data-testid="stNumberInput"] input { border-radius: 6px; }
    div[data-testid="stTextInput"] input  { border-radius: 6px; }
    div[data-testid="stTextArea"] textarea { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Constantes ────────────────────────────────────────────────────────────────
DIMENSOES = ["Cargo", "Controle", "Demandas", "Relacionamentos",
             "Apoio dos Colegas", "Apoio da Chefia", "Comunicação e Mudanças"]

INTERP_PADRAO = {
    "Demandas": "",
    "Controle": "",
    "Suporte gerencial": "",
    "Suporte entre pares": "",
    "Relacionamentos": "",
    "Papel": "",
    "Mudança": "",
}

# ── Estado inicial ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "empresa": "", "cnpj": "", "setor_avaliado": "Toda a empresa",
        "data_aplicacao": "", "total_colab": "", "total_resp": "",
        "taxa_resposta": "", "cidade": "", "n_minimo": 10,
        "psi_nome": "", "psi_crp": "", "psi_consult": "",
        "med_nome": "", "med_crm": "",
        "escores": {d: 65 for d in DIMENSOES},
        "interpretacoes": {d: "" for d in DIMENSOES},
        "setores": [],      # lista de dicts {nome, n, escores}
        "plano": [],        # lista de dicts {dim, prior, acao, resp, prazo}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Motor PDF (mesmo do script original) ─────────────────────────────────────
AZUL_ESCURO = colors.HexColor("#1a3557")
AZUL_MEDIO  = colors.HexColor("#2e6da4")
AZUL_CLARO  = colors.HexColor("#d6e4f0")
CINZA_TEXTO = colors.HexColor("#333333")
CINZA_LINHA = colors.HexColor("#e0e0e0")
VERDE   = colors.HexColor("#27ae60")
AMARELO = colors.HexColor("#f39c12")
VERMELHO= colors.HexColor("#e74c3c")

def estilo(nome, **kw):
    base = dict(fontName="Helvetica", fontSize=10,
                textColor=CINZA_TEXTO, leading=14, spaceAfter=4)
    base.update(kw)
    return ParagraphStyle(nome, **base)

def cor_escore(v):
    if v <= 20:  return colors.HexColor("#c0392b")
    if v <= 40:  return VERMELHO
    if v <= 60:  return AMARELO
    if v <= 80:  return VERDE
    return colors.HexColor("#1e8449")

def hex_escore(v):
    h = cor_escore(v).hexval()
    return "#" + h[2:] if h.startswith("0x") else h

def label_escore(v):
    if v <= 20:  return "Crítico"
    if v <= 40:  return "Ruim"
    if v <= 60:  return "Médio"
    if v <= 80:  return "Bom"
    return "Excelente"

def cor_label(v):
    if v <= 20:  return colors.HexColor("#c0392b")
    if v <= 40:  return colors.HexColor("#e74c3c")
    if v <= 60:  return colors.HexColor("#f39c12")
    if v <= 80:  return colors.HexColor("#27ae60")
    return colors.HexColor("#1e8449")

def hr_line():
    return HRFlowable(width="100%", thickness=1, color=AZUL_MEDIO,
                      spaceAfter=8, spaceBefore=4)

def secao(txt):
    S = estilo("Sec", fontName="Helvetica-Bold", fontSize=12,
               textColor=AZUL_ESCURO, spaceBefore=14, spaceAfter=6)
    return [Spacer(1, 6), Paragraph(txt, S), hr_line()]

def grafico_barras(resultados, titulo):
    dims = list(resultados.keys())
    vals = list(resultados.values())
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.barh(dims, vals, color=[hex_escore(v) for v in vals], height=0.55, zorder=2)
    ax.set_xlim(0, 100)
    ax.axvline(70, color="#27ae60", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(50, color="#f39c12", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Escore (0–100)", fontsize=8)
    ax.tick_params(axis='y', labelsize=8); ax.tick_params(axis='x', labelsize=7)
    ax.set_facecolor("#f8f9fa"); fig.patch.set_facecolor("white")
    ax.grid(axis='x', color='#dddddd', zorder=1)
    for bar, val in zip(bars, vals):
        ax.text(val + 1, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=8, fontweight='bold')
    ax.legend(handles=[
        mpatches.Patch(color="#1e8449", label="Excelente (81-100)"),
        mpatches.Patch(color="#27ae60", label="Bom (61-80)"),
        mpatches.Patch(color="#f39c12", label="Médio (41-60)"),
        mpatches.Patch(color="#e74c3c", label="Ruim (21-40)"),
        mpatches.Patch(color="#c0392b", label="Crítico (0-20)"),
    ], fontsize=7, loc="lower right")
    ax.set_title(titulo, fontsize=9, fontweight='bold', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig); buf.seek(0)
    return RLImage(buf, width=14 * cm, height=7 * cm)

def grafico_heatmap(validos):
    setores = list(validos.keys())
    data = np.array([[validos[s][d] for s in setores] for d in DIMENSOES])
    fig, ax = plt.subplots(figsize=(7, 3.8))
    im = ax.imshow(data, cmap='RdYlGn', vmin=0, vmax=100, aspect='auto')
    ax.set_xticks(range(len(setores))); ax.set_xticklabels(setores, fontsize=8)
    ax.set_yticks(range(len(DIMENSOES))); ax.set_yticklabels(DIMENSOES, fontsize=7.5)
    for i in range(len(DIMENSOES)):
        for j in range(len(setores)):
            val = data[i, j]
            ax.text(j, i, str(val), ha='center', va='center', fontsize=8,
                    fontweight='bold', color="white" if val < 40 or val > 85 else "black")
    plt.colorbar(im, ax=ax, shrink=0.8, label="Escore")
    ax.set_title("Comparativo por Setor", fontsize=9, fontweight='bold', pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig); buf.seek(0)
    return RLImage(buf, width=14 * cm, height=6.5 * cm)

def grafico_radar(validos):
    N = len(DIMENSOES)
    angulos = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]
    cores = ["#2e6da4", "#e74c3c", "#27ae60", "#f39c12", "#8e44ad"]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.set_facecolor("#f8f9fa"); fig.patch.set_facecolor("white")
    for i, (setor, res) in enumerate(validos.items()):
        vals = [res[d] for d in DIMENSOES] + [res[DIMENSOES[0]]]
        ax.plot(angulos, vals, 'o-', linewidth=1.5, color=cores[i % len(cores)], label=setor)
        ax.fill(angulos, vals, alpha=0.08, color=cores[i % len(cores)])
    ax.set_xticks(angulos[:-1]); ax.set_xticklabels(DIMENSOES, size=7)
    ax.set_ylim(0, 100); ax.set_yticks([25, 50, 70, 100])
    ax.set_yticklabels(["25", "50", "70", "100"], size=6, color="#888888")
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.15), fontsize=7)
    ax.set_title("Radar por Setor", size=9, fontweight='bold', pad=15)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig); buf.seek(0)
    return RLImage(buf, width=10 * cm, height=9 * cm)

def gerar_pdf_bytes(dados):
    buf = io.BytesIO()
    TW = A4[0] - 5 * cm
    S_BODY  = estilo("Body", alignment=TA_JUSTIFY, leading=15)
    S_LABEL = estilo("Lbl", fontName="Helvetica-Bold", fontSize=9, textColor=AZUL_ESCURO)
    S_SMALL = estilo("Sm", fontSize=8, textColor=colors.HexColor("#666666"))

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title="Laudo de Avaliação Psicossocial – HSE-IT")
    story = []

    n_min = dados.get("n_minimo", 10)
    validos    = {s["nome"]: s["escores"] for s in dados["setores"]
                  if s["n"] >= n_min and s["nome"].strip()}
    suprimidos = {s["nome"]: s["n"] for s in dados["setores"]
                  if s["n"] < n_min and s["nome"].strip()}

    # CAPA
    for txt, bg, fs in [
        ("LAUDO DE AVALIAÇÃO DE<br/>RISCOS PSICOSSOCIAIS", AZUL_ESCURO, 18),
        ("Instrumento: HSE Indicator Tool (HSE-IT)", AZUL_MEDIO, 13),
    ]:
        S = estilo(f"Cap{fs}", fontName="Helvetica-Bold", fontSize=fs,
                   textColor=colors.white, alignment=TA_CENTER, leading=fs+4)
        tb = Table([[Paragraph(txt, S)]], colWidths=[TW])
        tb.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("TOPPADDING",(0,0),(-1,-1),22 if fs==18 else 10),
            ("BOTTOMPADDING",(0,0),(-1,-1),12 if fs==18 else 10),
            ("LEFTPADDING",(0,0),(-1,-1),20),
        ]))
        story.append(tb)
    story.append(Spacer(1, 18))

    id_rows = [
        [Paragraph("Empresa:", S_LABEL),       Paragraph(dados["empresa"], S_BODY),
         Paragraph("CNPJ:", S_LABEL),           Paragraph(dados["cnpj"], S_BODY)],
        [Paragraph("Setor avaliado:", S_LABEL), Paragraph(dados["setor_avaliado"], S_BODY),
         Paragraph("Data de aplicação:", S_LABEL), Paragraph(dados["data_aplicacao"], S_BODY)],
        [Paragraph("Colaboradores:", S_LABEL),  Paragraph(dados["total_colab"], S_BODY),
         Paragraph("Respondentes:", S_LABEL),
         Paragraph(f"{dados['total_resp']} ({dados['taxa_resposta'] if '%' in str(dados['taxa_resposta']) else str(dados['taxa_resposta'])+'%'})", S_BODY)],
    ]
    id_tb = Table(id_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    id_tb.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[AZUL_CLARO,colors.white]),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
    ]))
    # Linha extra com data do relatório integrada
    data_row = Table([
        [Paragraph("Data do relatório:", S_LABEL),
         Paragraph(f"{datetime.today().strftime('%d/%m/%Y')} — {dados['cidade']}", S_BODY),
         Paragraph("", S_BODY), Paragraph("", S_BODY)],
    ], colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    data_row.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#eef3f8")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
    ]))
    story += [id_tb, data_row, Spacer(1,20)]

    # 1. NR-1
    story += secao("1. Contextualização Legal — NR-1 e Riscos Psicossociais")
    story.append(Paragraph(
        "A Norma Regulamentadora n.º 1 (NR-1), atualizada pela Portaria MTE n.º 1.419/2024, "
        "passou a exigir que todas as empresas brasileiras identifiquem, avaliem e controlem "
        "<b>riscos psicossociais</b> no âmbito do Programa de Gerenciamento de Riscos (PGR). "
        "A vigência iniciou-se em maio de 2025, com fiscalização efetiva prevista a partir "
        "de maio de 2026.", S_BODY))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        "Riscos psicossociais são fatores relativos à organização, ao conteúdo e ao ambiente "
        "de trabalho que, quando mal gerenciados, podem causar danos à saúde mental e física "
        "dos trabalhadores — incluindo estresse ocupacional, síndrome de burnout, ansiedade "
        "e depressão.", S_BODY))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        f"Este laudo documenta a avaliação dos riscos psicossociais em <b>{dados['empresa']}</b>, "
        "em conformidade com os requisitos da NR-1/GRO.", S_BODY))

    # 2. METODOLOGIA
    story.append(PageBreak())
    story += secao("2. Metodologia — HSE Indicator Tool (HSE-IT)")
    story.append(Paragraph(
        "O <b>HSE Indicator Tool (HSE-IT)</b> foi desenvolvido pelo Health and Safety Executive "
        "do Reino Unido. É um questionário validado internacionalmente, de domínio público, "
        "amplamente utilizado em avaliações psicossociais ocupacionais, aplicado de forma "
        "<b>anônima e voluntária</b> por meio de plataforma digital de coleta anônima, "
        "cobrindo sete dimensões-chave:", S_BODY))
    story.append(Spacer(1,6))
    dim_rows = [["Dimensão", "O que avalia"]] + [
        ["Cargo","Clareza de função, adequação das responsabilidades e ausência de conflito de papéis"],
        ["Controle","Autonomia, participação nas decisões e ritmo de trabalho"],
        ["Demandas","Carga de trabalho, ritmo, horas e pressão por produção"],
        ["Relacionamentos","Conflitos interpessoais e comportamentos inaceitáveis no trabalho"],
        ["Apoio dos Colegas","Cooperação, suporte e senso de pertencimento entre pares"],
        ["Apoio da Chefia","Incentivo, feedback e apoio das lideranças diretas"],
        ["Comunicação e Mudanças","Transparência na comunicação e envolvimento nas mudanças organizacionais"],
    ]
    dt = Table(dim_rows, colWidths=[5.5*cm, 11.5*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
    ]))
    story.append(dt)
    story.append(Spacer(1,8))
    story.append(Paragraph(
        "Escores de 0 a 100 por dimensão: "
        "<b>Excelente</b> (81–100) | <b>Bom</b> (61–80) | <b>Médio</b> (41–60) | "
        "<b>Ruim</b> (21–40) | <b>Crítico</b> (0–20).", S_BODY))
    story.append(PageBreak())
    story += secao("3. Resultados Gerais")
    story.append(grafico_barras(dados["escores"], "Resultados Gerais por Dimensão"))
    story.append(Spacer(1,10))
    res_rows = [["Dimensão","Escore","Classificação"]]
    for dim, val in dados["escores"].items():
        res_rows.append([dim, str(val), label_escore(val)])
    res_tb = Table(res_rows, colWidths=[8*cm,3*cm,6*cm])
    res_ts = TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("ALIGN",(1,0),(2,-1),"CENTER"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
    ])
    for i, (dim, val) in enumerate(dados["escores"].items(), 1):
        res_ts.add("TEXTCOLOR",(2,i),(2,i),cor_label(val))
        res_ts.add("FONTNAME",(2,i),(2,i),"Helvetica-Bold")
    res_tb.setStyle(res_ts)
    story.append(res_tb)

    # 4. ANÁLISE POR DIMENSÃO
    story += secao("4. Análise por Dimensão")
    for dim, interp in dados["interpretacoes"].items():
        val = dados["escores"].get(dim, 0)
        hdr = Table([[
            Paragraph(f"<b>{dim}</b>", estilo(f"DH{dim[:4]}", fontName="Helvetica-Bold",
                fontSize=10, textColor=colors.white)),
            Paragraph(f"Escore: <b>{val}</b> — {label_escore(val)}",
                estilo(f"DE{dim[:4]}", fontSize=9, textColor=colors.white, alignment=TA_CENTER)),
        ]], colWidths=[10*cm,7*cm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),AZUL_MEDIO),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(KeepTogether([hdr, Spacer(1,4),
                                   Paragraph(interp or "(sem interpretação preenchida)", S_BODY),
                                   Spacer(1,10)]))

    # 5. LIMITAÇÕES
    story.append(PageBreak())
    story += secao("5. Limitações Metodológicas")
    story.append(Paragraph(
        "A apresentação transparente das limitações deste instrumento e desta aplicação "
        "é parte integrante das boas práticas em saúde ocupacional e protege juridicamente "
        "todos os responsáveis técnicos envolvidos.", S_BODY))
    story.append(Spacer(1,10))
    AMARELO_BG = colors.HexColor("#fff8e1")
    AMARELO_BD = colors.HexColor("#f39c12")
    taxa = dados["taxa_resposta"]
    if "%" not in str(taxa): taxa = str(taxa) + "%"
    limitacoes = [
        ("Mensuração de percepção, não de diagnóstico clínico",
         "O HSE-IT avalia a <i>percepção</i> dos colaboradores sobre o ambiente psicossocial "
         "de trabalho. Escores desfavoráveis indicam necessidade de investigação e intervenção, "
         "mas não constituem diagnóstico clínico individual de transtorno mental. A avaliação "
         "clínica de cada trabalhador é competência exclusiva de profissionais de saúde habilitados."),
        ("Viés de resposta e contexto da coleta",
         "Respostas podem ser influenciadas pelo momento organizacional durante a aplicação "
         "(período de reestruturação, demissões, campanhas internas, etc.), pelo grau de "
         "confiança dos colaboradores no anonimato e pela adesão voluntária. Taxa de resposta "
         f"abaixo de 70% aumenta o risco de viés de seleção. Nesta aplicação, a taxa foi de "
         f"<b>{taxa}</b>."),
        ("Validade temporal",
         f"Os resultados refletem o estado percebido no período de coleta "
         f"(<b>{dados['data_aplicacao']}</b>). Mudanças organizacionais relevantes ocorridas "
         "após essa data podem alterar significativamente o panorama psicossocial. "
         "Recomenda-se reaplicação anual ou após eventos organizacionais de grande impacto."),
        ("Ausência de dados normativos brasileiros consolidados",
         "O HSE-IT foi originalmente desenvolvido e normatizado no Reino Unido. Embora amplamente "
         "utilizado no Brasil, ainda não existem tabelas normativas nacionais publicadas para "
         "comparação setorial. Os pontos de corte adotados (em faixas de 20 pontos) são uma "
         "convenção metodológica adotada nesta aplicação."),
        ("Limitações de anonimato em grupos pequenos",
         f"Grupos com menos de <b>{n_min} respondentes</b> não têm escores publicados "
         "individualmente neste laudo. Em amostras muito pequenas, mesmo com anonimato declarado, "
         "colaboradores podem sentir-se identificáveis, comprometendo a sinceridade das respostas "
         "e a representatividade dos resultados."),
        ("O instrumento não cobre todos os fatores de risco",
         "O HSE-IT abrange sete dimensões psicossociais centrais, mas não esgota o espectro "
         "de riscos ocupacionais de natureza psicossocial. Fatores como violência no trabalho, "
         "assédio moral ou sexual e condições físicas do ambiente devem ser investigados por "
         "outros meios complementares no âmbito do PGR."),
    ]
    for tit, txt in limitacoes:
        bloco = Table([[Paragraph(f"<b>{tit}</b>",
            estilo(f"LT{hash(tit)%9999}", fontName="Helvetica-Bold",
                   fontSize=9, textColor=AZUL_ESCURO))]], colWidths=[TW])
        bloco.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),AZUL_CLARO),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
        ]))
        story.append(KeepTogether([bloco, Spacer(1,3),
                                   Paragraph(txt, S_BODY), Spacer(1,10)]))
    if suprimidos:
        aviso_its = [Paragraph(
            f"Atenção: Setor(es) com n < {n_min} — escores suprimidos",
            estilo("AvTit", fontName="Helvetica-Bold", fontSize=9,
                   textColor=colors.HexColor("#7d4e00")))]
        for s_nome, s_n in suprimidos.items():
            aviso_its.append(Paragraph(
                f"• <b>{s_nome}</b>: {s_n} respondente(s). Dados incorporados apenas à análise geral.",
                estilo(f"AvB{s_nome[:4]}", fontSize=9, leading=14,
                       textColor=colors.HexColor("#7d4e00"))))
        av_tb = Table([[aviso_its]], colWidths=[TW])
        av_tb.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),AMARELO_BG),("BOX",(0,0),(-1,-1),1,AMARELO_BD),
            ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
            ("LEFTPADDING",(0,0),(-1,-1),12),
        ]))
        story.append(av_tb)

    # 6. SETORES
    if validos:
        story.append(PageBreak())
        story += secao("6. Resultados por Setor")
        story.append(Paragraph(
            f"Apenas setores com número de respondentes igual ou superior ao limiar mínimo "
            f"({n_min}) são apresentados individualmente. Os gráficos abaixo permitem "
            "identificar diferenças de exposição a riscos psicossociais entre os setores "
            "avaliados, orientando ações focadas.", S_BODY))
        story.append(Spacer(1,8))
        story += secao("6.1 Visão Comparativa")
        story.append(grafico_heatmap(validos))
        story.append(Spacer(1,12))
        story.append(grafico_radar(validos))
        for idx, (setor, res) in enumerate(validos.items(), start=2):
            n_s = next((s["n"] for s in dados["setores"] if s["nome"]==setor), "?")
            story.append(PageBreak())
            story += secao(f"6.{idx} Detalhamento — {setor} (n={n_s})")
            story.append(grafico_barras(res, f"Dimensões — {setor}"))
            story.append(Spacer(1,8))
            r2 = [["Dimensão","Escore","Classificação"]]
            for d, v in res.items(): r2.append([d, str(v), label_escore(v)])
            tb2 = Table(r2, colWidths=[8*cm,3*cm,6*cm])
            ts2 = TableStyle([
                ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
                ("ALIGN",(1,0),(2,-1),"CENTER"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
                ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1),8),
                ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
            ])
            for i,(d,v) in enumerate(res.items(),1):
                ts2.add("TEXTCOLOR",(2,i),(2,i),cor_escore(v))
                ts2.add("FONTNAME",(2,i),(2,i),"Helvetica-Bold")
            tb2.setStyle(ts2); story.append(tb2); story.append(Spacer(1,12))
            critico = [(d,v) for d,v in res.items() if v<=20]
            ruim    = [(d,v) for d,v in res.items() if 21<=v<=40]
            medio   = [(d,v) for d,v in res.items() if 41<=v<=60]
            if critico:
                story.append(Paragraph("<b>Dimensões críticas (0–20) — intervenção imediata:</b>", S_BODY))
                for d,v in critico:
                    story.append(Paragraph(f"• <b>{d}</b> ({v}) — requer intervenção imediata neste setor.", S_BODY))
                story.append(Spacer(1,6))
            if ruim:
                story.append(Paragraph("<b>Dimensões ruins (21–40) — intervenção prioritária:</b>", S_BODY))
                for d,v in ruim:
                    story.append(Paragraph(f"• <b>{d}</b> ({v}) — requer intervenção prioritária neste setor.", S_BODY))
                story.append(Spacer(1,6))
            if medio:
                story.append(Paragraph("<b>Dimensões médias (41–60) — atenção preventiva:</b>", S_BODY))
                for d,v in medio:
                    story.append(Paragraph(f"• <b>{d}</b> ({v}) — monitorar e implantar melhorias preventivas.", S_BODY))

    # 7. PLANO DE AÇÃO
    story.append(PageBreak())
    story += secao("7. Plano de Ação Recomendado")
    story.append(Paragraph(
        "As recomendações abaixo foram priorizadas com base nos escores obtidos e nas "
        "boas práticas de gestão de riscos psicossociais. Recomenda-se nova aplicação "
        "do instrumento após a implementação para verificar a eficácia das ações.", S_BODY))
    story.append(Spacer(1,8))
    def pa_cell(txt, bold=False, cor=None):
        st2 = estilo(f"PAC{hash(txt)%9999}", fontSize=7.5, leading=11)
        if bold: st2.fontName = "Helvetica-Bold"
        if cor:  st2.textColor = cor
        return Paragraph(txt, st2)
    pa_header = [pa_cell(h, bold=True) for h in ["Dimensão","Prior.","Ação recomendada","Responsável","Prazo"]]
    pa_rows = [pa_header]
    prior_cor = {"Alta":VERMELHO,"Média":AMARELO,"Baixa":VERDE}
    for row in dados["plano"]:
        if not any(row.values()): continue
        cor_p = prior_cor.get(row.get("prior",""), CINZA_TEXTO)
        pa_rows.append([
            pa_cell(row.get("dim","")),
            pa_cell(row.get("prior",""), bold=True, cor=cor_p),
            pa_cell(row.get("acao","")),
            pa_cell(row.get("resp","")),
            pa_cell(row.get("prazo","")),
        ])
    pa = Table(pa_rows, colWidths=[3.2*cm,1.8*cm,7.5*cm,3.2*cm,2*cm])
    pa.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
    ]))
    story.append(pa)

    # 8. PGR / SESMT
    story.append(PageBreak())
    story += secao("8. Orientações para Inserção no PGR — SESMT")
    story.append(Paragraph(
        "Esta seção destina-se ao SESMT (Serviço Especializado em Engenharia de Segurança e "
        "em Medicina do Trabalho) e apresenta orientações objetivas para a incorporação dos "
        "riscos psicossociais identificados ao <b>Programa de Gerenciamento de Riscos (PGR)</b>, "
        "conforme exigido pela NR-1/GRO.", S_BODY))
    story.append(Spacer(1,10))

    story += secao("8.1 Como Incorporar ao PGR")
    for tit_o, txt_o in [
        ("Identificação do perigo",
         "Os fatores psicossociais avaliados — Cargo, Controle, Demandas, Relacionamentos, "
         "Apoio dos Colegas, Apoio da Chefia e Comunicação e Mudanças — devem ser registrados "
         "como <b>perigos de natureza psicossocial</b> no inventário de riscos do PGR, com "
         "referência ao instrumento utilizado (HSE-IT) e à data de aplicação."),
        ("Uso dos escores como indicador de probabilidade",
         "Os escores por dimensão representam o nível de exposição percebida ao fator "
         "psicossocial e podem ser utilizados como indicador de <b>probabilidade</b> na "
         "matriz de risco do PGR. A conversão depende do formato da matriz adotada pelo SESMT:"),
        ("Severidade — julgamento do SESMT",
         "A severidade do risco é de julgamento exclusivo dos profissionais do SESMT, "
         "considerando o contexto da empresa, o histórico de saúde dos trabalhadores, a "
         "natureza das atividades e outras fontes do PGR (PCMSO, atestados, afastamentos, "
         "NR-17, etc.). Recomenda-se que dimensões com escore abaixo de 40 sejam discutidas "
         "pelos profissionais do SESMT responsáveis antes da classificação final de risco."),
        ("Medidas de controle",
         "As ações do Plano (Seção 7) devem ser transcritas para o campo de "
         "<i>medidas de prevenção e controle</i> do PGR, com responsável, prazo e "
         "forma de monitoramento definidos."),
        ("Monitoramento e revisão",
         "Recomenda-se reaplicação do HSE-IT a cada <b>12 meses</b> ou após mudanças "
         "organizacionais relevantes. Os resultados devem ser comparados ao baseline "
         "deste laudo e registrados como evidência de monitoramento no PGR."),
        ("Documentação e evidências",
         "Mantenha arquivados: este laudo assinado, o formulário aplicado, os dados brutos "
         "anonimizados e os registros de ações implementadas. Esses documentos constituem "
         "evidência perante fiscalização do MTE."),
    ]:
        story.append(KeepTogether([
            Paragraph(f"<b>{tit_o}</b>",
                estilo(f"OT{hash(tit_o)%9999}", fontName="Helvetica-Bold",
                       fontSize=9, textColor=AZUL_MEDIO)),
            Paragraph(txt_o, S_BODY), Spacer(1,8),
        ]))

    # Tabela de conversão de escores por tipo de matriz
    story.append(Spacer(1,4))
    def mc(txt, bold=False, center=False):
        return Paragraph(txt, estilo(f"MC{hash(txt)%9999}", fontSize=8, leading=11,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=TA_CENTER if center else TA_JUSTIFY))

    matriz_rows = [
        [mc("Matriz",True,True), mc("Intervalos de escore",True,True),
         mc("Nível de probabilidade sugerido",True,True)],
        [mc("3×3",True,True), mc("0–33 / 34–66 / 67–100",center=True),
         mc("Alta / Média / Baixa",center=True)],
        [mc("4×4",True,True), mc("0–25 / 26–50 / 51–75 / 76–100",center=True),
         mc("Alta / Média-alta / Média-baixa / Baixa",center=True)],
        [mc("5×5",True,True), mc("0–20 / 21–40 / 41–60 / 61–80 / 81–100",center=True),
         mc("Muito alta / Alta / Média / Baixa / Muito baixa",center=True)],
    ]
    mt = Table(matriz_rows, colWidths=[2*cm, 6.5*cm, 8.5*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("BACKGROUND",(0,1),(0,-1),AZUL_CLARO),
        ("ROWBACKGROUNDS",(1,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
        ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
    ]))
    story.append(mt)
    story.append(Spacer(1,12))

    story += secao("8.2 Tabela de Riscos no Formato GRO — Exemplo Ilustrativo")
    story.append(Paragraph(
        "A tabela abaixo é um <b>exemplo ilustrativo</b> para orientar a estruturação dos "
        "registros no inventário de riscos do PGR, seguindo a estrutura do GRO. "
        "Os perigos, agravos à saúde e medidas de controle devem ser revisados e adaptados "
        "pelo SESMT conforme a realidade da organização, podendo ser complementados com "
        "outras fontes do PGR (PCMSO, NR-17, CIPA, etc.).", S_BODY))
    story.append(Spacer(1,8))

    def gro_cell(txt, bold=False, italic=False):
        fn = "Helvetica-Bold" if bold else "Helvetica-Oblique" if italic else "Helvetica"
        return Paragraph(txt, estilo(f"GC{hash(txt)%9999}",
            fontSize=7, leading=10, fontName=fn))

    CINZA_ITER = colors.HexColor("#f0f0f0")
    gro_rows = [[gro_cell(h, bold=True) for h in
        ["Fonte / Fator de Risco","Perigo Psicossocial","Possível Agravo à Saúde",
         "Medidas de Prevenção e Controle","Prazo","Resp."]]]

    gro_exemplos = [
        ("Organização do trabalho (Comunicação e Mudanças)",
         "Ausência de comunicação prévia sobre mudanças organizacionais",
         "Ansiedade, insegurança, adoecimento mental",
         "Protocolo de comunicação de mudanças; canal de escuta das equipes",
         "60 dias", "Diretoria"),
        ("Relação hierárquica (Apoio da Chefia)",
         "Liderança sem práticas estruturadas de apoio e feedback",
         "Burnout, desmotivação, absenteísmo",
         "Programa de desenvolvimento de lideranças; 1:1 mensais",
         "90 dias", "RH"),
        ("Conteúdo do trabalho (Cargo)",
         "Ambiguidade de funções e sobreposição de responsabilidades",
         "Estresse, conflito interpessoal",
         "Revisão de descrições de cargo; mapeamento de responsabilidades",
         "120 dias", "RH"),
        ("Carga de trabalho (Demandas)",
         "Volume e prazos excessivos em períodos de pico",
         "Fadiga, erros, afastamentos",
         "Monitoramento de horas extras; redistribuição de carga",
         "90 dias", "Gestão"),
    ]
    for r in gro_exemplos:
        gro_rows.append([gro_cell(cel) for cel in r])

    # 2 linhas em branco para o SESMT preencher
    for _ in range(2):
        gro_rows.append([gro_cell("A preencher pelo SESMT", italic=True)] * 6)

    gro = Table(gro_rows, colWidths=[3*cm, 3.2*cm, 2.8*cm, 4*cm, 1.5*cm, 1.2*cm])
    gro_ts = TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
        # Linhas "a preencher" em itálico e fundo diferente
        ("BACKGROUND",(0,5),(-1,6),CINZA_ITER),
        ("TEXTCOLOR",(0,5),(-1,6),colors.HexColor("#888888")),
    ])
    gro.setStyle(gro_ts)
    story.append(gro)

    # 9. ASSINATURAS
    story.append(Spacer(1,30))
    story += secao("9. Responsáveis Técnicos")
    psi_consult = dados.get("psi_consult","").strip()
    ass = Table([[
        Paragraph(
            f"_______________________________<br/><b>{dados['psi_nome']}</b><br/>"
            f"{dados['psi_crp']}"
            + (f"<br/>{psi_consult}" if psi_consult else "")
            + "<br/>Psicóloga — Responsável técnica pela avaliação",
            estilo("A1", alignment=TA_CENTER, fontSize=9)),
        Paragraph(
            f"_______________________________<br/><b>{dados['med_nome']}</b><br/>"
            f"{dados['med_crm']}<br/>Médico do Trabalho Consultor",
            estilo("A2", alignment=TA_CENTER, fontSize=9)),
    ]], colWidths=[TW/2]*2)
    ass.setStyle(TableStyle([
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(ass)

    def cabecalho_rodape(canvas, doc):
        canvas.saveState()
        w, h = A4
        # Cabeçalho — só a partir da página 2
        if doc.page > 1:
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(colors.HexColor("#555555"))
            consult = dados.get("psi_consult", "").strip()
            if consult:
                canvas.drawString(2.5*cm, h - 1.5*cm, consult)
            canvas.drawRightString(w - 2.5*cm, h - 1.5*cm, "Laudo Psicossocial HSE-IT")
            canvas.setStrokeColor(colors.HexColor("#dddddd"))
            canvas.setLineWidth(0.5)
            canvas.line(2.5*cm, h - 1.7*cm, w - 2.5*cm, h - 1.7*cm)
        # Rodapé — todas as páginas
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawCentredString(w/2, 1.2*cm,
            f"Laudo de Avaliação Psicossocial – {dados['empresa']} | HSE-IT | Pág. {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=cabecalho_rodape, onLaterPages=cabecalho_rodape)
    buf.seek(0)
    return buf.read()

# ══════════════════════════════════════════════════════════════════════════════
#  INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🧠 Gerador de Laudo Psicossocial HSE-IT</h1>
    <p>Preencha as abas abaixo e clique em <strong>Gerar PDF</strong> para baixar o laudo completo.</p>
</div>
""", unsafe_allow_html=True)

# ── Salvar / Carregar rascunho ────────────────────────────────────────────────
def estado_para_json():
    return json.dumps({
        "empresa": st.session_state.get("empresa",""),
        "cnpj": st.session_state.get("cnpj",""),
        "setor_avaliado": st.session_state.get("setor_avaliado",""),
        "data_aplicacao": st.session_state.get("data_aplicacao",""),
        "total_colab": st.session_state.get("total_colab",""),
        "total_resp": st.session_state.get("total_resp",""),
        "taxa_resposta": st.session_state.get("taxa_resposta",""),
        "cidade": st.session_state.get("cidade",""),
        "n_minimo": st.session_state.get("n_minimo", 10),
        "psi_nome": st.session_state.get("psi_nome",""),
        "psi_crp": st.session_state.get("psi_crp",""),
        "psi_consult": st.session_state.get("psi_consult",""),
        "med_nome": st.session_state.get("med_nome",""),
        "med_crm": st.session_state.get("med_crm",""),
        "escores": st.session_state.get("escores", {d:65 for d in DIMENSOES}),
        "interpretacoes": st.session_state.get("interpretacoes", {d:"" for d in DIMENSOES}),
        "setores": st.session_state.get("setores", []),
        "plano": st.session_state.get("plano", []),
    }, ensure_ascii=False, indent=2)

def json_para_estado(dados):
    for k in ["empresa","cnpj","setor_avaliado","data_aplicacao","total_colab",
              "total_resp","taxa_resposta","cidade","psi_nome","psi_crp",
              "psi_consult","med_nome","med_crm"]:
        if k in dados: st.session_state[k] = dados[k]
    if "n_minimo"       in dados: st.session_state["n_minimo"]       = dados["n_minimo"]
    if "escores"        in dados: st.session_state["escores"]        = dados["escores"]
    if "interpretacoes" in dados: st.session_state["interpretacoes"] = dados["interpretacoes"]
    if "setores"        in dados: st.session_state["setores"]        = dados["setores"]
    if "plano"          in dados: st.session_state["plano"]          = dados["plano"]

col_s1, col_s2, col_s3 = st.columns([1,1,4])
with col_s1:
    empresa_nome = st.session_state.get("empresa","rascunho") or "rascunho"
    st.download_button(
        "💾 Salvar rascunho",
        data=estado_para_json(),
        file_name=f"rascunho_{empresa_nome.replace(' ','_')}.json",
        mime="application/json",
        use_container_width=True,
    )
with col_s2:
    uploaded = st.file_uploader("📂 Carregar rascunho", type="json",
                                 label_visibility="collapsed")
    if uploaded:
        try:
            dados_json = json.load(uploaded)
            json_para_estado(dados_json)
            st.success("Rascunho carregado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar: {e}")


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Identificação",
    "📊 Escores Gerais",
    "📝 Interpretações",
    "🏢 Setores",
    "✅ Plano de Ação",
])

# ── ABA 1: IDENTIFICAÇÃO ──────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">Dados da Empresa</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    st.session_state.empresa        = c1.text_input("Nome da empresa *", st.session_state.empresa)
    st.session_state.cnpj           = c2.text_input("CNPJ *", st.session_state.cnpj)
    c3, c4 = st.columns([2,1])
    st.session_state.setor_avaliado = c3.text_input("Setor avaliado *", st.session_state.setor_avaliado)
    st.session_state.data_aplicacao = c4.text_input("Data de aplicação *", st.session_state.data_aplicacao, placeholder="DD/MM/AAAA")
    c5, c6, c7, c8 = st.columns(4)
    st.session_state.total_colab    = c5.text_input("Total de colaboradores", st.session_state.total_colab)
    st.session_state.total_resp     = c6.text_input("Total de respondentes", st.session_state.total_resp)
    st.session_state.taxa_resposta  = c7.text_input("Taxa de resposta", st.session_state.taxa_resposta, placeholder="Ex: 85%")
    st.session_state.cidade         = c8.text_input("Cidade", st.session_state.cidade)
    st.session_state.n_minimo       = st.number_input("N mínimo por setor", min_value=1, max_value=50,
                                                       value=st.session_state.n_minimo)
    st.markdown('<div class="info-box">💡 Setores com menos respondentes que o N mínimo serão suprimidos automaticamente do laudo para preservar o anonimato.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Responsáveis Técnicos</div>', unsafe_allow_html=True)
    c9, c10 = st.columns([2,1])
    st.session_state.psi_nome    = c9.text_input("Nome da psicóloga *", st.session_state.psi_nome)
    st.session_state.psi_crp     = c10.text_input("CRP *", st.session_state.psi_crp, placeholder="CRP 06/123456")
    st.session_state.psi_consult = st.text_input("Consultoria da psicóloga (opcional)", st.session_state.psi_consult)
    c11, c12 = st.columns([2,1])
    st.session_state.med_nome    = c11.text_input("Nome do médico do trabalho *", st.session_state.med_nome)
    st.session_state.med_crm     = c12.text_input("CRM — RQE *", st.session_state.med_crm, placeholder="CRM SP 12345 — RQE 6789")

# ── ABA 2: ESCORES GERAIS ─────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">Escores por Dimensão (0 a 100)</div>', unsafe_allow_html=True)
    st.caption("Preencha com os valores calculados a partir das respostas coletadas.")
    for dim in DIMENSOES:
        val = st.session_state.escores.get(dim, 65)
        if val <= 20:   cor = "🔴"
        elif val <= 40: cor = "🟠"
        elif val <= 60: cor = "🟡"
        elif val <= 80: cor = "🟢"
        else:           cor = "✅"
        lbl = label_escore(val)
        c1, c2 = st.columns([4,1])
        novo = c1.slider(f"{cor} **{dim}**", 0, 100, val, key=f"slider_{dim}")
        c2.metric("", f"{novo}", lbl)
        st.session_state.escores[dim] = novo

# ── ABA 3: INTERPRETAÇÕES ─────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Análise Qualitativa por Dimensão</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-box">⚠️ Preencha todas as sete dimensões. Campos vazios aparecerão como "(sem interpretação preenchida)" no laudo.</div>', unsafe_allow_html=True)
    for dim in DIMENSOES:
        val = st.session_state.escores.get(dim, 65)
        if val <= 20:   cor = "🔴"
        elif val <= 40: cor = "🟠"
        elif val <= 60: cor = "🟡"
        elif val <= 80: cor = "🟢"
        else:           cor = "✅"
        txt = st.text_area(
            f"{cor} **{dim}** — Escore: {val} ({label_escore(val)})",
            st.session_state.interpretacoes.get(dim, ""),
            height=100, key=f"interp_{dim}"
        )
        st.session_state.interpretacoes[dim] = txt

# ── ABA 4: SETORES ────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">Resultados por Setor</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">💡 Se a empresa não tiver setores distintos, deixe esta aba em branco. O laudo ficará apenas com a análise geral.</div>', unsafe_allow_html=True)

    n_setores = st.number_input("Quantos setores deseja incluir?", 0, 10,
                                 max(1, len(st.session_state.setores)) if st.session_state.setores else 0,
                                 key="n_setores_input")

    # Ajustar lista de setores
    while len(st.session_state.setores) < n_setores:
        st.session_state.setores.append({"nome":"","n":0,"escores":{d:65 for d in DIMENSOES}})
    st.session_state.setores = st.session_state.setores[:n_setores]

    for i, setor in enumerate(st.session_state.setores):
        with st.expander(f"Setor {i+1}: {setor['nome'] or '(sem nome)'}", expanded=True):
            c1, c2 = st.columns([3,1])
            setor["nome"] = c1.text_input("Nome do setor", setor["nome"], key=f"s_nome_{i}")
            setor["n"]    = c2.number_input("N respondentes", 0, 9999, setor["n"], key=f"s_n_{i}")
            n_min = st.session_state.n_minimo
            if setor["n"] > 0 and setor["n"] < n_min:
                st.markdown(f'<div class="alert-box">⚠️ Este setor tem {setor["n"]} respondente(s) — abaixo do mínimo de {n_min}. Será suprimido automaticamente do laudo.</div>', unsafe_allow_html=True)
            # Linha 1: primeiras 4 dimensões
            cols1 = st.columns(4)
            for j, dim in enumerate(DIMENSOES[:4]):
                setor["escores"][dim] = cols1[j].number_input(
                    dim, 0, 100, setor["escores"].get(dim, 65),
                    key=f"s_{i}_{j}")
            # Linha 2: últimas 3 dimensões (+ coluna vazia para alinhar)
            cols2 = st.columns(4)
            for j, dim in enumerate(DIMENSOES[4:]):
                setor["escores"][dim] = cols2[j].number_input(
                    dim, 0, 100, setor["escores"].get(dim, 65),
                    key=f"s_{i}_{j+4}")

# ── ABA 5: PLANO DE AÇÃO ─────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-header">Plano de Ação Recomendado</div>', unsafe_allow_html=True)
    st.markdown('<div class="alert-box">⚠️ No campo Prioridade, use exatamente: Alta, Média ou Baixa (com acento e maiúscula).</div>', unsafe_allow_html=True)

    n_acoes = st.number_input("Quantas ações deseja incluir?", 0, 20,
                               max(1, len(st.session_state.plano)) if st.session_state.plano else 3,
                               key="n_acoes_input")
    while len(st.session_state.plano) < n_acoes:
        st.session_state.plano.append({"dim":"","prior":"Alta","acao":"","resp":"","prazo":""})
    st.session_state.plano = st.session_state.plano[:n_acoes]

    for i, row in enumerate(st.session_state.plano):
        with st.expander(f"Ação {i+1}: {row['dim'] or '(sem dimensão)'}", expanded=(i<3)):
            c1, c2 = st.columns([2,1])
            row["dim"]   = c1.text_input("Dimensão", row["dim"], key=f"p_dim_{i}")
            row["prior"] = c2.selectbox("Prioridade", ["Alta","Média","Baixa"],
                                         ["Alta","Média","Baixa"].index(row["prior"]) if row["prior"] in ["Alta","Média","Baixa"] else 0,
                                         key=f"p_prior_{i}")
            row["acao"]  = st.text_area("Ação recomendada", row["acao"], height=80, key=f"p_acao_{i}")
            c3, c4 = st.columns(2)
            row["resp"]  = c3.text_input("Responsável", row["resp"], key=f"p_resp_{i}")
            row["prazo"] = c4.text_input("Prazo", row["prazo"], key=f"p_prazo_{i}", placeholder="Ex: 90 dias")

# ── BOTÃO GERAR PDF ───────────────────────────────────────────────────────────
st.divider()
col_btn, col_info = st.columns([1,3])
with col_btn:
    gerar = st.button("📄 Gerar PDF", type="primary", use_container_width=True)

if gerar:
    if not st.session_state.empresa:
        st.error("Preencha pelo menos o nome da empresa antes de gerar o PDF.")
    else:
        with st.spinner("Gerando o laudo... aguarde alguns segundos."):
            dados = {
                "empresa":        st.session_state.empresa,
                "cnpj":           st.session_state.cnpj,
                "setor_avaliado": st.session_state.setor_avaliado,
                "data_aplicacao": st.session_state.data_aplicacao,
                "total_colab":    st.session_state.total_colab,
                "total_resp":     st.session_state.total_resp,
                "taxa_resposta":  st.session_state.taxa_resposta,
                "cidade":         st.session_state.cidade,
                "n_minimo":       st.session_state.n_minimo,
                "psi_nome":       st.session_state.psi_nome,
                "psi_crp":        st.session_state.psi_crp,
                "psi_consult":    st.session_state.psi_consult,
                "med_nome":       st.session_state.med_nome,
                "med_crm":        st.session_state.med_crm,
                "escores":        st.session_state.escores,
                "interpretacoes": st.session_state.interpretacoes,
                "setores":        st.session_state.setores,
                "plano":          st.session_state.plano,
            }
            try:
                pdf_bytes = gerar_pdf_bytes(dados)
                nome = f"Laudo_HSE-IT_{dados['empresa'].replace(' ','_')}_{datetime.today().strftime('%Y%m%d')}.pdf"
                st.success("✅ Laudo gerado com sucesso!")
                st.download_button(
                    label="⬇️ Baixar PDF",
                    data=pdf_bytes,
                    file_name=nome,
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erro ao gerar o PDF: {e}")
