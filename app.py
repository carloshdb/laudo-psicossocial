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

def texto_automatico(dim, escore):
    """Retorna o texto interpretativo automático para uma dimensão e escore."""
    if escore <= 20:   faixa = "critico"
    elif escore <= 40: faixa = "ruim"
    elif escore <= 60: faixa = "medio"
    elif escore <= 80: faixa = "bom"
    else:              faixa = "excelente"

    textos = {
        "Cargo": {
            "excelente": "A clareza sobre funções e responsabilidades é um ponto de força desta organização. Os colaboradores demonstram ampla compreensão de seu papel, o que contribui para a estabilidade operacional, reduz conflitos por sobreposição de tarefas e favorece o engajamento. Recomenda-se manter as práticas atuais e revisitar este indicador nas próximas aplicações.",
            "bom":       "A maioria dos colaboradores demonstra boa compreensão de suas funções e responsabilidades. Há oportunidades pontuais de melhoria, especialmente em situações de transição de equipe ou mudança de processo. Recomenda-se comunicação periódica sobre papéis e inclusão deste tema nas avaliações de desempenho.",
            "medio":     "Parte dos colaboradores relata incerteza sobre suas funções ou percebe sobreposição de responsabilidades com colegas. Esta condição pode gerar conflitos, retrabalho e sobrecarga cognitiva. Recomenda-se revisão das descrições de cargo e alinhamento formal de expectativas entre líderes e equipes.",
            "ruim":      "Há percepção relevante de falta de clareza sobre funções e responsabilidades. Os colaboradores relatam dificuldade em compreender o que se espera deles, o que impacta a produtividade e pode contribuir para conflitos interpessoais e sentimento de injustiça. Intervenção estruturada é indicada.",
            "critico":   "A ausência de clareza sobre cargo e responsabilidades configura um fator de risco psicossocial de alta magnitude. Os dados indicam que grande parte dos colaboradores não compreende seu papel na organização, condição associada a estresse crônico, esgotamento ocupacional e alta rotatividade. Recomenda-se intervenção imediata e prioritária.",
        },
        "Controle": {
            "excelente": "Os colaboradores percebem elevado grau de autonomia e participação nas decisões que afetam seu trabalho. Este é um fator de proteção relevante, associado a maior satisfação, engajamento e resiliência frente às demandas. Recomenda-se manter e ampliar as práticas participativas existentes.",
            "bom":       "O nível de autonomia e influência sobre o próprio trabalho é satisfatório na percepção da maioria dos colaboradores. Há espaço para ampliar a participação em decisões específicas, especialmente nas equipes onde o índice é mais baixo. Recomenda-se monitoramento e ações pontuais de descentralização.",
            "medio":     "Parte dos colaboradores percebe limitações relevantes na autonomia sobre seu trabalho e pouca participação nas decisões que os afetam. Esta condição pode gerar sensação de falta de controle, desmotivação e redução do comprometimento. Recomenda-se mapear onde estão as principais restrições e ampliar os espaços de participação.",
            "ruim":      "A percepção de baixa autonomia e exclusão das decisões é expressiva. Os colaboradores relatam pouca influência sobre o ritmo, os métodos e a organização do próprio trabalho. Esta condição está associada a estresse ocupacional, absenteísmo e queda de produtividade. Intervenção é indicada.",
            "critico":   "O nível de autonomia percebida é criticamente baixo. Os colaboradores relatam ausência quase total de controle sobre seu trabalho e exclusão sistemática das decisões. Esta condição é um dos preditores mais robustos de esgotamento ocupacional na literatura e requer intervenção imediata.",
        },
        "Demandas": {
            "excelente": "A carga de trabalho é percebida como adequada e gerenciável pela grande maioria dos colaboradores. O ritmo, o volume e os prazos estão bem calibrados, o que favorece a produtividade sustentável e o bem-estar. Recomenda-se manter o monitoramento, especialmente em períodos de pico.",
            "bom":       "A carga de trabalho é gerenciável na maior parte do tempo, com pontos de atenção em períodos específicos de pico. A maioria dos colaboradores consegue organizar suas demandas sem comprometimento significativo do bem-estar. Recomenda-se monitorar os períodos críticos e antecipar reforços quando necessário.",
            "medio":     "Parte dos colaboradores relata dificuldade em lidar com o volume, o ritmo ou os prazos do trabalho. Há indícios de sobrecarga recorrente que pode estar impactando a qualidade das entregas e o bem-estar. Recomenda-se mapeamento dos gargalos e revisão da distribuição de tarefas.",
            "ruim":      "A sobrecarga de trabalho é percebida de forma expressiva. Os colaboradores relatam dificuldade frequente em cumprir as demandas dentro dos prazos sem comprometer sua saúde ou qualidade de vida. Esta condição está associada a fadiga crônica, erros operacionais e afastamentos. Intervenção é indicada.",
            "critico":   "O nível de sobrecarga percebida é crítico. Os dados indicam que as demandas de trabalho estão consistentemente além da capacidade de resposta dos colaboradores, configurando risco elevado de adoecimento, afastamentos e acidentes. Recomenda-se intervenção imediata com revisão estrutural da carga de trabalho.",
        },
        "Relacionamentos": {
            "excelente": "O ambiente relacional entre os colaboradores é percebido como muito positivo. Não foram identificados padrões relevantes de conflito, comportamentos inadequados ou situações de assédio. Este é um fator de proteção importante para a saúde mental coletiva. Recomenda-se manter as práticas que sustentam este clima.",
            "bom":       "O clima relacional é positivo, com baixa incidência de conflitos interpessoais ou comportamentos inadequados. Situações pontuais podem existir mas não configuram padrão preocupante. Recomenda-se manter canais de comunicação abertos e monitorar nas próximas aplicações.",
            "medio":     "Há relatos de conflitos interpessoais ou comportamentos inadequados que merecem atenção. Embora não configurem padrão generalizado, indicam fragilidades no clima relacional que podem se intensificar sem intervenção. Recomenda-se investigar os contextos específicos e reforçar as políticas de conduta.",
            "ruim":      "Os conflitos interpessoais e comportamentos inadequados são percebidos de forma relevante por uma parcela expressiva dos colaboradores. Esta condição impacta diretamente o bem-estar, a cooperação e a produtividade das equipes. Intervenção estruturada é indicada, incluindo investigação de situações específicas.",
            "critico":   "O nível de conflitos e comportamentos inadequados percebido é crítico. Os dados sugerem padrões sistemáticos de deterioração relacional que podem incluir situações de assédio moral ou sexual. Esta condição configura risco psicossocial grave e requer apuração imediata, com garantia de espaço seguro de escuta para os colaboradores.",
        },
        "Apoio dos Colegas": {
            "excelente": "O suporte entre pares é percebido como forte e consistente. Os colaboradores sentem que podem contar com colegas em momentos de dificuldade, o que contribui para a resiliência coletiva e a coesão das equipes. Recomenda-se manter as práticas que fortalecem este vínculo.",
            "bom":       "O apoio entre colegas é percebido como satisfatório pela maioria dos colaboradores. Há coesão e cooperação nas equipes, com espaço para aprimoramento em situações específicas. Recomenda-se monitorar e fortalecer as práticas de integração.",
            "medio":     "Parte dos colaboradores relata percepção limitada de apoio entre pares. A cooperação entre equipes pode ser inconsistente, com alguns grupos ou turnos mais isolados. Recomenda-se promover oportunidades de integração e revisar se a organização do trabalho isola colaboradores.",
            "ruim":      "A percepção de baixo suporte entre pares é expressiva. Os colaboradores relatam dificuldade em contar com colegas em situações de sobrecarga ou dificuldade. Esta condição compromete a resiliência das equipes e pode agravar o impacto de outras dimensões desfavoráveis. Intervenção é indicada.",
            "critico":   "O nível de suporte percebido entre pares é criticamente baixo. Os dados indicam isolamento relacional expressivo no ambiente de trabalho, condição associada a maior vulnerabilidade ao adoecimento mental. Recomenda-se intervenção imediata com foco na reconstrução dos vínculos de equipe.",
        },
        "Apoio da Chefia": {
            "excelente": "O suporte das lideranças é percebido como forte e consistente. Os colaboradores sentem que seus gestores estão presentes, acessíveis e comprometidos com o bem-estar das equipes. Este é um fator de proteção relevante e deve ser mantido como prática institucional.",
            "bom":       "O apoio das lideranças é percebido como satisfatório pela maioria dos colaboradores. Os gestores são vistos como acessíveis e comprometidos, com espaço para aprimoramento em aspectos específicos de feedback e suporte individualizado. Recomenda-se monitoramento e desenvolvimento contínuo.",
            "medio":     "Parte dos colaboradores percebe limitações no suporte oferecido pelas lideranças diretas. Aspectos como feedback, reconhecimento e disponibilidade para escuta podem não estar sendo atendidos de forma consistente. Recomenda-se capacitação pontual de lideranças e estabelecimento de práticas de acompanhamento.",
            "ruim":      "A percepção de baixo apoio das lideranças é expressiva. Os colaboradores relatam dificuldade em acessar suporte, feedback ou reconhecimento de seus gestores. Esta condição impacta diretamente o engajamento, a saúde mental e a produtividade das equipes. Intervenção estruturada é indicada.",
            "critico":   "O nível de suporte percebido das lideranças é criticamente baixo. Os dados indicam que os gestores não estão exercendo adequadamente seu papel de apoio e proteção das equipes, condição fortemente associada a esgotamento ocupacional, absenteísmo e rotatividade elevada. Recomenda-se intervenção imediata.",
        },
        "Comunicação e Mudanças": {
            "excelente": "A comunicação organizacional e a gestão de mudanças são percebidas como transparentes e participativas. Os colaboradores se sentem informados e envolvidos nos processos que afetam seu trabalho, o que favorece a adaptabilidade e o engajamento. Recomenda-se manter as práticas vigentes.",
            "bom":       "A comunicação é percebida como adequada pela maioria dos colaboradores, com boa gestão dos processos de mudança. Há espaço para ampliar a participação e antecipar informações em situações de transição. Recomenda-se monitoramento e reforço dos canais de comunicação existentes.",
            "medio":     "Parte dos colaboradores relata percepção de comunicação insuficiente ou tardia, especialmente em contextos de mudança organizacional. Esta condição pode gerar insegurança, resistência e queda de engajamento. Recomenda-se revisar os canais e os processos de comunicação interna.",
            "ruim":      "A percepção de falhas na comunicação e na gestão de mudanças é expressiva. Os colaboradores relatam sentir-se mal informados ou excluídos dos processos decisórios que afetam seu trabalho. Esta condição está associada a insegurança, resistência e deterioração do clima organizacional. Intervenção é indicada.",
            "critico":   "O nível de percepção de falhas na comunicação e na gestão de mudanças é crítico. Os dados indicam que os colaboradores se sentem sistematicamente desinformados e excluídos, condição que pode gerar crise de confiança institucional e impactar gravemente o clima e a saúde das equipes. Recomenda-se intervenção imediata.",
        },
    }
    return textos.get(dim, {}).get(faixa, "")


def acoes_automaticas(dim, escore):
    """Retorna lista de ações recomendadas para uma dimensão e escore."""
    if escore <= 40:   grupo = "critico_ruim"
    elif escore <= 60: grupo = "medio"
    else:              grupo = "bom_excelente"

    acoes = {
        "Cargo": {
            "critico_ruim":   [
                "Realizar levantamento das descrições de cargo existentes e identificar lacunas de clareza",
                "Promover reuniões de alinhamento entre líderes e equipes para redefinição de responsabilidades",
                "Implementar ou revisar o processo de integração (onboarding) com foco em clareza de papel",
                "Criar mecanismo periódico de revisão de atribuições em casos de mudança de equipe ou processo",
                "Capacitar lideranças para comunicar expectativas de forma clara e estruturada",
            ],
            "medio":          [
                "Revisar e atualizar as descrições de cargo com participação dos próprios colaboradores",
                "Incluir alinhamento de expectativas como pauta regular nas avaliações de desempenho",
                "Criar canal para que colaboradores possam reportar sobreposições ou ambiguidades de função",
                "Monitorar este indicador na próxima aplicação do HSE-IT",
            ],
            "bom_excelente":  ["Manter as práticas atuais e monitorar nas próximas aplicações"],
        },
        "Controle": {
            "critico_ruim":   [
                "Mapear os processos com menor grau de autonomia e avaliar possibilidade de descentralização",
                "Criar espaços estruturados de participação das equipes nas decisões que afetam seu trabalho",
                "Revisar modelos de supervisão que possam estar gerando excesso de controle",
                "Capacitar lideranças em gestão participativa e delegação efetiva",
                "Implementar mecanismos de escuta ativa para que colaboradores sinalizem restrições percebidas",
            ],
            "medio":          [
                "Identificar áreas ou equipes com menor percepção de autonomia e agir de forma focada",
                "Ampliar a participação de colaboradores em reuniões de planejamento e revisão de processos",
                "Estimular lideranças a delegar decisões operacionais às equipes",
                "Monitorar este indicador na próxima aplicação do HSE-IT",
            ],
            "bom_excelente":  ["Manter as práticas participativas e monitorar nas próximas aplicações"],
        },
        "Demandas": {
            "critico_ruim":   [
                "Realizar diagnóstico detalhado de carga de trabalho por setor e função",
                "Revisar estruturalmente a distribuição de tarefas, prazos e metas",
                "Monitorar horas extras e estabelecer limites formais de jornada",
                "Implementar mecanismos de reforço de equipe em períodos de pico previsíveis",
                "Criar canal seguro para que colaboradores sinalizem sobrecarga sem receio de represálias",
            ],
            "medio":          [
                "Mapear os gargalos de demanda e os períodos de maior pressão",
                "Estabelecer práticas de planejamento que antecipem reforços em períodos críticos",
                "Incluir gestão de demandas como pauta nas reuniões de liderança",
                "Monitorar este indicador na próxima aplicação do HSE-IT",
            ],
            "bom_excelente":  ["Manter o monitoramento da carga de trabalho, especialmente em períodos de pico"],
        },
        "Relacionamentos": {
            "critico_ruim":   [
                "Investigar situações específicas de conflito com sigilo e imparcialidade",
                "Implementar ou revisar política de prevenção ao assédio moral e sexual",
                "Oferecer espaço de escuta confidencial para colaboradores",
                "Promover ações de comunicação não violenta e gestão de conflitos",
                "Capacitar lideranças para identificar e mediar conflitos",
            ],
            "medio":          [
                "Reforçar o código de conduta e os canais de comunicação disponíveis",
                "Incluir clima relacional como pauta em reuniões de equipe",
                "Promover atividades de integração entre equipes",
                "Capacitar lideranças para identificar sinais precoces de conflito",
                "Garantir que todos os colaboradores conheçam os canais de denúncia disponíveis",
            ],
            "bom_excelente":  ["Manter o ambiente positivo e monitorar sinais de deterioração nas próximas aplicações"],
        },
        "Apoio dos Colegas": {
            "critico_ruim":   [
                "Promover atividades de integração e fortalecimento de vínculos entre equipes",
                "Revisar se a organização do trabalho isola colaboradores ou dificulta a colaboração",
                "Estimular práticas de mentoria e apoio mútuo entre pares",
                "Avaliar se a competição interna está prejudicando o senso de equipe",
                "Criar rituais de equipe que reforcem a cooperação e o pertencimento",
            ],
            "medio":          [
                "Criar oportunidades regulares de troca e colaboração entre equipes",
                "Reconhecer publicamente comportamentos de apoio e cooperação",
                "Promover integração entre colaboradores de diferentes turnos ou áreas",
                "Estimular práticas de onboarding com envolvimento dos colegas",
                "Incluir cooperação como critério nas avaliações de desempenho",
            ],
            "bom_excelente":  ["Manter as práticas de integração e monitorar nas próximas aplicações"],
        },
        "Apoio da Chefia": {
            "critico_ruim":   [
                "Realizar diagnóstico de estilo de liderança e identificar lacunas de competências gerenciais",
                "Implementar programa estruturado de desenvolvimento de lideranças com foco em escuta e feedback",
                "Estabelecer reuniões individuais regulares entre líderes e colaboradores",
                "Criar mecanismo de avaliação de liderança pelos liderados",
                "Garantir que líderes tenham suporte institucional para apoiar suas equipes",
            ],
            "medio":          [
                "Oferecer capacitação pontual em feedback e comunicação para lideranças",
                "Incluir suporte à equipe como critério nas avaliações de desempenho dos gestores",
                "Estimular lideranças a realizar check-ins regulares com suas equipes",
                "Criar espaço seguro para colaboradores sinalizarem falta de suporte",
                "Reconhecer e valorizar lideranças que demonstram apoio efetivo às equipes",
            ],
            "bom_excelente":  ["Manter as práticas de desenvolvimento de lideranças e monitorar nas próximas aplicações"],
        },
        "Comunicação e Mudanças": {
            "critico_ruim":   [
                "Implementar protocolo formal de comunicação para mudanças organizacionais",
                "Garantir que colaboradores sejam informados com antecedência e tenham espaço para perguntas",
                "Criar canal de escuta ativa durante processos de mudança",
                "Envolver representantes das equipes no planejamento de mudanças",
                "Nomear responsável pela comunicação interna em cada processo de transição",
            ],
            "medio":          [
                "Revisar os canais de comunicação interna e avaliar sua efetividade",
                "Incluir comunicação transparente como pauta em reuniões de liderança",
                "Criar boletim ou comunicado periódico com atualizações relevantes para as equipes",
                "Garantir que mudanças operacionais sejam comunicadas antes de implementadas",
                "Criar espaço para perguntas anônimas sobre mudanças em curso",
            ],
            "bom_excelente":  ["Manter as práticas de comunicação e monitorar nas próximas aplicações"],
        },
    }
    return acoes.get(dim, {}).get(grupo, [])

# ── Estado inicial ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "empresa": "", "cnpj": "", "setor_avaliado": "Toda a empresa",
        "data_aplicacao": "", "total_colab": "", "total_resp": "",
        "taxa_resposta": "", "cidade": "", "n_minimo": 5,
        "q36": 0.0, "q37": 0.0,
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
    # KeepTogether garante que o título nunca fica isolado no fim da página
    bloco = KeepTogether([Spacer(1, 6), Paragraph(txt, S), hr_line(), Spacer(1, 4)])
    return [bloco]

def grafico_barras(resultados, titulo):
    # Garantir ordem canônica e inverter para que Cargo fique no topo
    dims_ord = [d for d in DIMENSOES if d in resultados]
    vals_ord  = [resultados[d] for d in dims_ord]
    dims_ord  = dims_ord[::-1]
    vals_ord  = vals_ord[::-1]

    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.barh(dims_ord, vals_ord, color=[hex_escore(v) for v in vals_ord], height=0.55, zorder=2)
    ax.set_xlim(0, 100)
    ax.axvline(60, color="#27ae60", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(40, color="#f39c12", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Escore (0–100)", fontsize=8)
    ax.tick_params(axis='y', labelsize=8); ax.tick_params(axis='x', labelsize=7)
    ax.set_facecolor("#f8f9fa"); fig.patch.set_facecolor("white")
    ax.grid(axis='x', color='#dddddd', zorder=1)
    for bar, val in zip(bars, vals_ord):
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
        [Paragraph("Empresa:", S_LABEL),          Paragraph(dados["empresa"], S_BODY),
         Paragraph("CNPJ:", S_LABEL),              Paragraph(dados["cnpj"], S_BODY)],
        [Paragraph("Setor avaliado:", S_LABEL),    Paragraph(dados["setor_avaliado"], S_BODY),
         Paragraph("Data de aplicação:", S_LABEL), Paragraph(dados["data_aplicacao"], S_BODY)],
        [Paragraph("Colaboradores:", S_LABEL),     Paragraph(dados["total_colab"], S_BODY),
         Paragraph("Respondentes:", S_LABEL),
         Paragraph(f"{dados['total_resp']} ({dados['taxa_resposta'] if '%' in str(dados['taxa_resposta']) else str(dados['taxa_resposta'])+'%'})", S_BODY)],
        [Paragraph("Data do relatório:", S_LABEL),
         Paragraph(f"{datetime.today().strftime('%d/%m/%Y')} — {dados['cidade']}", S_BODY),
         Paragraph("", S_BODY), Paragraph("", S_BODY)],
    ]
    id_tb = Table(id_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    id_tb.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[AZUL_CLARO, colors.white]),
        ("TOPPADDING",   (0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",  (0,0),(-1,-1), 0.3, CINZA_LINHA),
        ("BOX",   (0,0),(-1,-1), 0.5, AZUL_MEDIO),
        # Mesclar colunas 1-3 da última linha (valor + células vazias)
        ("SPAN",  (1,3), (3,3)),
        ("BACKGROUND", (0,3),(-1,3), colors.HexColor("#eef3f8")),
    ]))
    story += [id_tb, Spacer(1,20)]

    # 1. NR-1
    story += secao("1. Contextualização Legal — NR-1 e Riscos Psicossociais")
    story.append(Paragraph(
        "A Norma Regulamentadora n.º 1 (NR-1), atualizada pela Portaria MTE n.º 1.419/2024 "
        "e com vigência plena a partir de 26 de maio de 2026, passou a exigir que todas as "
        "empresas brasileiras identifiquem, avaliem e controlem fatores de risco psicossociais "
        "no âmbito do Programa de Gerenciamento de Riscos (PGR). Este laudo documenta o "
        f"cumprimento dessa exigência por <b>{dados['empresa']}</b>, por meio de avaliação "
        "estruturada e metodologicamente fundamentada.", S_BODY))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        "Riscos psicossociais são fatores relativos à organização, ao conteúdo e ao ambiente "
        "de trabalho que, quando mal gerenciados, podem causar danos à saúde mental e física "
        "dos trabalhadores — incluindo estresse ocupacional, esgotamento ocupacional, ansiedade "
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
    dt = Table(dim_rows, colWidths=[4.5*cm, 12.5*cm])
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
        "Os escores são calculados em escala de 0 a 100. Para permitir uma análise granular "
        "e facilitar a incorporação dos resultados ao PGR, convencionou-se a seguinte divisão "
        "em <b>cinco faixas de classificação</b>:", S_BODY))
    story.append(Spacer(1,6))
    faixa_rows = [
        [Paragraph(h, estilo(f"FH{i}", fontName="Helvetica-Bold", fontSize=8.5,
                   textColor=colors.white)) for i, h in enumerate(["Faixa","Escore","Interpretação","Implicação para o PGR"])],
        [Paragraph("Excelente", estilo("FE", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#1e8449"))),
         Paragraph("81–100", estilo("FEv", fontSize=8.5, alignment=TA_CENTER)),
         Paragraph("Fator de proteção consolidado", estilo("FEt", fontSize=8.5)),
         Paragraph("Monitorar e manter as práticas vigentes", estilo("FEp", fontSize=8.5))],
        [Paragraph("Bom", estilo("FB", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#27ae60"))),
         Paragraph("61–80", estilo("FBv", fontSize=8.5, alignment=TA_CENTER)),
         Paragraph("Condição satisfatória com pontos de melhoria", estilo("FBt", fontSize=8.5)),
         Paragraph("Ações preventivas pontuais", estilo("FBp", fontSize=8.5))],
        [Paragraph("Médio", estilo("FM", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#f39c12"))),
         Paragraph("41–60", estilo("FMv", fontSize=8.5, alignment=TA_CENTER)),
         Paragraph("Exposição moderada ao fator de risco", estilo("FMt", fontSize=8.5)),
         Paragraph("Intervenção preventiva recomendada", estilo("FMp", fontSize=8.5))],
        [Paragraph("Ruim", estilo("FR", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#e74c3c"))),
         Paragraph("21–40", estilo("FRv", fontSize=8.5, alignment=TA_CENTER)),
         Paragraph("Exposição relevante; risco presente", estilo("FRt", fontSize=8.5)),
         Paragraph("Intervenção prioritária indicada", estilo("FRp", fontSize=8.5))],
        [Paragraph("Crítico", estilo("FC", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#c0392b"))),
         Paragraph("0–20", estilo("FCv", fontSize=8.5, alignment=TA_CENTER)),
         Paragraph("Exposição intensa; fator de risco prioritário", estilo("FCt", fontSize=8.5)),
         Paragraph("Intervenção imediata obrigatória", estilo("FCp", fontSize=8.5))],
    ]
    ft = Table(faixa_rows, colWidths=[2.5*cm, 2*cm, 6*cm, 6.2*cm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),AZUL_ESCURO),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,AZUL_CLARO]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("ALIGN",(1,0),(1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.3,CINZA_LINHA),("BOX",(0,0),(-1,-1),0.5,AZUL_MEDIO),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(ft)
    story.append(PageBreak())
    story += secao("3. Resultados Gerais")

    # Intro textual com taxa de adesão
    taxa_str = dados.get("taxa_resposta", "")
    story.append(Paragraph(
        f"Esta seção apresenta os resultados consolidados da avaliação psicossocial de "
        f"<b>{dados['empresa']}</b>, realizada em {dados['data_aplicacao']}. "
        f"Do total de <b>{dados['total_colab']}</b> colaboradores, <b>{dados['total_resp']}</b> "
        f"responderam ao instrumento, correspondendo a uma <b>taxa de adesão de {taxa_str}</b>.",
        S_BODY))
    story.append(Spacer(1, 10))
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

    # 3b. INDICADORES DE DESFECHO (Q36/Q37)
    q36 = dados.get("q36", 0.0)
    q37 = dados.get("q37", 0.0)
    if q36 > 0 or q37 > 0:
        story.append(Spacer(1, 14))
        story += secao("3.1 Indicadores de Desfecho")
        story.append(Paragraph(
            "As questões extras 36 e 37 avaliam indicadores de desfecho que complementam "
            "os escores dimensionais do HSE-IT. A questão 36 mensura a satisfação geral com "
            "o trabalho e a questão 37 avalia a autopercepção de saúde dos respondentes. "
            "Ambas utilizam escala Likert de 5 pontos, e seus resultados são convertidos para "
            "a mesma escala de 0 a 100 utilizada nas sete dimensões, facilitando a comparação. "
            "Os escores são classificados nas mesmas faixas: Excelente (81–100), Bom (61–80), "
            "Médio (41–60), Ruim (21–40) e Crítico (0–20).",
            S_BODY))
        story.append(Spacer(1, 8))

        def media_para_escore(v):
            """Converte média 1–5 para escore 0–100."""
            if v <= 0: return 0.0
            return round((v - 1) / 4 * 100, 1)

        def_rows = [[
            Paragraph(h, estilo(f"DFH{i}", fontName="Helvetica-Bold", fontSize=9,
                      textColor=colors.white, alignment=TA_CENTER if i > 1 else TA_JUSTIFY))
            for i, h in enumerate(["Questão", "Enunciado", "Média (1–5)", "Escore (0–100)", "Classificação"])
        ]]
        for q_num, q_val, q_txt in [
            (36, q36, "Satisfação geral com o trabalho"),
            (37, q37, "Autopercepção de saúde"),
        ]:
            if q_val > 0:
                escore = media_para_escore(q_val)
                def_rows.append([
                    Paragraph(f"Q{q_num}", estilo(f"DFQ{q_num}", fontName="Helvetica-Bold",
                              fontSize=9, textColor=AZUL_ESCURO, alignment=TA_CENTER)),
                    Paragraph(q_txt, S_BODY),
                    Paragraph(f"{q_val:.1f}", estilo(f"DFM{q_num}", fontSize=9, alignment=TA_CENTER)),
                    Paragraph(f"{escore:.0f}", estilo(f"DFV{q_num}", fontName="Helvetica-Bold",
                              fontSize=9, textColor=cor_label(escore), alignment=TA_CENTER)),
                    Paragraph(label_escore(escore), estilo(f"DFL{q_num}", fontName="Helvetica-Bold",
                              fontSize=9, textColor=cor_label(escore), alignment=TA_CENTER)),
                ])

        def_tb = Table(def_rows, colWidths=[2*cm, 7*cm, 2.5*cm, 2.5*cm, 3*cm])
        def_ts = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), AZUL_ESCURO),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, AZUL_CLARO]),
            ("TOPPADDING",    (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("GRID",  (0,0), (-1,-1), 0.3, CINZA_LINHA),
            ("BOX",   (0,0), (-1,-1), 0.5, AZUL_MEDIO),
            ("VALIGN",(0,0), (-1,-1), "MIDDLE"),
        ])
        def_tb.setStyle(def_ts)
        story.append(def_tb)
    story.append(PageBreak())
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
         f"abaixo de 60% aumenta o risco de viés de seleção. Nesta aplicação, a taxa foi de "
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

    # 7. PLANO DE AÇÃO
    story.append(PageBreak())
    story += secao("7. Plano de Ação Recomendado")
    story.append(Paragraph(
        "As recomendações abaixo foram priorizadas com base nos escores obtidos e nas "
        "boas práticas de gestão de riscos psicossociais. Recomenda-se nova aplicação "
        "do instrumento após a implementação para verificar a eficácia das ações.", S_BODY))
    story.append(Spacer(1,8))

    def pa_cell(txt, bold=False, cor=None, size=7.5, white=False):
        st2 = estilo(f"PAC{hash(txt)%9999}", fontSize=size, leading=11)
        if bold:  st2.fontName = "Helvetica-Bold"
        if white: st2.textColor = colors.white
        elif cor: st2.textColor = cor
        return Paragraph(txt, st2)

    # Agrupar plano por (dimensão, prioridade) — até 3 ações por grupo numa célula
    from collections import defaultdict, OrderedDict
    grupos = OrderedDict()
    for row in dados["plano"]:
        if not any(row.values()): continue
        key = (row.get("dim",""), row.get("prior","Alta"))
        if key not in grupos:
            grupos[key] = {"acoes": [], "resp": row.get("resp",""), "prazo": row.get("prazo","")}
        if len(grupos[key]["acoes"]) < 3:
            acao = row.get("acao","").strip()
            if acao:
                grupos[key]["acoes"].append(acao)
        # último resp/prazo preenchido vence
        if row.get("resp"): grupos[key]["resp"] = row["resp"]
        if row.get("prazo"): grupos[key]["prazo"] = row["prazo"]

    prior_cor = {"Alta": VERMELHO, "Média": AMARELO, "Baixa": VERDE}

    pa_header = [
        pa_cell(h, bold=True, white=True)
        for h in ["Dimensão", "Prior.", "Ações recomendadas", "Responsável", "Prazo"]
    ]
    pa_rows = [pa_header]
    for (dim, prior), grupo in grupos.items():
        cor_p = prior_cor.get(prior, CINZA_TEXTO)
        acoes_txt = "<br/>".join(
            f"{i+1}. {a}" for i, a in enumerate(grupo["acoes"])
        ) if grupo["acoes"] else "—"
        pa_rows.append([
            pa_cell(dim),
            pa_cell(prior, bold=True, cor=cor_p),
            Paragraph(acoes_txt, estilo(f"PAAT{hash(acoes_txt)%9999}", fontSize=7.5, leading=12)),
            pa_cell(grupo["resp"]),
            pa_cell(grupo["prazo"]),
        ])

    pa = Table(pa_rows, colWidths=[3.2*cm, 1.8*cm, 7.5*cm, 3.2*cm, 2*cm])
    pa.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), AZUL_ESCURO),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, AZUL_CLARO]),
        ("TOPPADDING",  (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 5), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID",  (0,0), (-1,-1), 0.3, CINZA_LINHA),
        ("BOX",   (0,0), (-1,-1), 0.5, AZUL_MEDIO),
    ]))
    story.append(pa)

    # 7b. ORIENTAÇÕES PARA GESTÃO DOS RISCOS PSICOSSOCIAIS
    story.append(PageBreak())
    story += secao("7.1 Orientações para Gestão dos Riscos Psicossociais Identificados")
    story.append(Paragraph(
        "<i>Nota: O conteúdo desta seção é de caráter orientativo e não substitui o julgamento "
        "clínico e técnico dos profissionais de saúde e segurança do trabalho responsáveis "
        "pela organização.</i>", S_BODY))
    story.append(Spacer(1, 8))

    NOME_RISCO = {
        "Cargo":                  "Falta de clareza sobre cargo e responsabilidades",
        "Controle":               "Baixa autonomia e participação no trabalho",
        "Demandas":               "Sobrecarga de trabalho e pressão por produção",
        "Relacionamentos":        "Conflitos interpessoais e comportamentos inadequados",
        "Apoio dos Colegas":      "Baixo suporte social entre pares",
        "Apoio da Chefia":        "Baixo suporte gerencial e de liderança",
        "Comunicação e Mudanças": "Gestão inadequada de mudanças organizacionais",
    }

    def escore_para_prob(v):
        if v <= 20:  return 5
        if v <= 40:  return 4
        if v <= 60:  return 3
        if v <= 80:  return 2
        return 1

    SEV_POR_DIM = {
        "Cargo":                  1,
        "Controle":               2,
        "Demandas":               3,
        "Relacionamentos":        2,
        "Apoio dos Colegas":      1,
        "Apoio da Chefia":        2,
        "Comunicação e Mudanças": 2,
    }

    def escore_para_sev(dim, v=None):
        return SEV_POR_DIM.get(dim, 1)

    MATRIZ_5X5 = {
        (1,1):("1","Mínimo"),  (1,2):("2","Baixo"),   (1,3):("3","Baixo"),   (1,4):("4","Médio"),  (1,5):("5","Médio"),
        (2,1):("2","Baixo"),   (2,2):("4","Baixo"),   (2,3):("6","Médio"),   (2,4):("8","Médio"),  (2,5):("10","Alto"),
        (3,1):("3","Baixo"),   (3,2):("6","Médio"),   (3,3):("9","Médio"),   (3,4):("12","Alto"),  (3,5):("15","Alto"),
        (4,1):("4","Médio"),   (4,2):("8","Médio"),   (4,3):("12","Alto"),   (4,4):("16","Crítico"),(4,5):("20","Crítico"),
        (5,1):("5","Médio"),   (5,2):("10","Alto"),   (5,3):("15","Alto"),   (5,4):("20","Crítico"),(5,5):("25","Crítico"),
    }
    COR_NIVEL_M = {
        "Mínimo": colors.HexColor("#bdc3c7"),
        "Baixo":  VERDE,
        "Médio":  AMARELO,
        "Alto":   VERMELHO,
        "Crítico":colors.HexColor("#c0392b"),
    }
    COR_BG_M = {
        "Mínimo": colors.HexColor("#d5d8dc"),
        "Baixo":  colors.HexColor("#a9dfbf"),
        "Médio":  colors.HexColor("#fdebd0"),
        "Alto":   colors.HexColor("#f5b7b1"),
        "Crítico":colors.HexColor("#c0392b"),
    }
    COR_TXT_M = {"Crítico": colors.white}

    story.append(Paragraph(
        "Os riscos psicossociais identificados são apresentados com a probabilidade estimada "
        "a partir dos escores HSE-IT (1 a 5, onde 5 indica maior probabilidade) e uma sugestão "
        "de severidade (1 a 5) como ponto de partida para os profissionais de saúde e segurança "
        "do trabalho. O resultado da matriz 5x5 é obtido multiplicando probabilidade x severidade. "
        "<b>A severidade e o resultado final são de responsabilidade exclusiva dos profissionais "
        "de S&amp;ST</b>, que devem considerar o contexto da organização, o histórico de saúde "
        "e outras fontes do PGR.*", S_BODY))
    story.append(Spacer(1, 8))

    dims_risco = [(d, v) for d, v in dados["escores"].items() if v <= 80]
    if dims_risco:
        def gc(txt, bold=False, center=False, cor=None, white=False):
            fn = "Helvetica-Bold" if bold else "Helvetica"
            tc = colors.white if white else (cor if cor else CINZA_TEXTO)
            return Paragraph(txt, estilo(f"GC{hash(txt+fn)%9999}",
                fontSize=7.5, leading=11, fontName=fn, textColor=tc,
                alignment=TA_CENTER if center else TA_JUSTIFY))

        gest_rows = [[
            gc(h, bold=True, white=True, center=(i>1))
            for i, h in enumerate(["Dimensão / Fator de Risco", "Escore HSE-IT",
                                   "Probabilidade*\n(1-5)", "Severidade sugerida*\n(1-5)",
                                   "Resultado\n(PxS)", "Classificação\nsugerida*"])
        ]]
        for dim, val in sorted(dims_risco, key=lambda x: DIMENSOES.index(x[0]) if x[0] in DIMENSOES else 99):
            prob = escore_para_prob(val)
            sev  = escore_para_sev(dim)
            res_num, res_class = MATRIZ_5X5.get((prob, sev), ("—", "—"))
            cor_res = COR_NIVEL_M.get(res_class, CINZA_TEXTO)
            gest_rows.append([
                gc(f"<b>{dim}</b><br/><i>{NOME_RISCO.get(dim,'')}</i>"),
                gc(str(val), center=True),
                gc(str(prob), bold=True, center=True),
                gc(str(sev), center=True),
                gc(res_num, bold=True, center=True, cor=cor_res),
                gc(res_class, bold=True, center=True, cor=cor_res),
            ])

        gest_tb = Table(gest_rows, colWidths=[5.2*cm, 1.8*cm, 2.2*cm, 2.5*cm, 2.0*cm, 2.6*cm])
        gest_tb.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), AZUL_ESCURO),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, AZUL_CLARO]),
            ("TOPPADDING",    (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("GRID",  (0,0), (-1,-1), 0.3, CINZA_LINHA),
            ("BOX",   (0,0), (-1,-1), 0.5, AZUL_MEDIO),
            ("VALIGN",(0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(gest_tb)
        story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Referência visual — Matriz 5x5 (Probabilidade x Severidade):</b>", S_BODY))
    story.append(Spacer(1, 4))

    def mcell(txt, nivel=None, bold=False):
        bg = COR_BG_M.get(nivel, colors.white) if nivel else colors.white
        tc = COR_TXT_M.get(nivel, colors.HexColor("#222222"))
        return Paragraph(txt, estilo(f"MC{hash(txt+str(nivel))%9999}",
            fontSize=7, leading=10, fontName="Helvetica-Bold" if bold else "Helvetica",
            textColor=tc, alignment=TA_CENTER))

    mx_header = [mcell("")] + [mcell(f"S={s}", bold=True) for s in range(1,6)]
    mx_rows = [mx_header]
    for p in range(5, 0, -1):
        row = [mcell(f"P={p}", bold=True)]
        for s in range(1, 6):
            num, nivel = MATRIZ_5X5[(p,s)]
            row.append(mcell(f"{num}\n{nivel}", nivel=nivel))
        mx_rows.append(row)

    mx_tb = Table(mx_rows, colWidths=[1.5*cm]+[2.5*cm]*5)
    mx_ts = TableStyle([
        ("TOPPADDING",  (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("GRID",  (0,0), (-1,-1), 0.5, colors.HexColor("#aaaaaa")),
        ("BOX",   (0,0), (-1,-1), 1.0, AZUL_MEDIO),
        ("VALIGN",(0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,0), AZUL_CLARO),
        ("BACKGROUND", (0,0), (0,-1), AZUL_CLARO),
    ])
    for ri, p in enumerate(range(5, 0, -1), start=1):
        for ci, s in enumerate(range(1, 6), start=1):
            _, nivel = MATRIZ_5X5[(p,s)]
            mx_ts.add("BACKGROUND", (ci, ri), (ci, ri), COR_BG_M.get(nivel, colors.white))
    mx_tb.setStyle(mx_ts)
    story.append(mx_tb)
    story.append(Spacer(1, 10))

    sev_titulo = Paragraph("<b>Referência de severidade sugerida por dimensão — ponto de partida para os profissionais de S&amp;ST:</b>", S_BODY)
    story.append(Spacer(1, 4))
    sev_rows = [[
        Paragraph(h, estilo(f"SH{i}", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white))
        for i, h in enumerate(["Dimensão", "Severidade sugerida", "Justificativa"])
    ]]
    sev_dados = [
        ("Cargo",                  "1", "Ambiguidade de papel gera desconforto e conflito, mas raramente adoecimento grave de forma isolada"),
        ("Controle",               "2", "Baixa autonomia sustentada associa-se a ansiedade e desmotivação crônicas"),
        ("Demandas",               "3", "Sobrecarga é um dos preditores mais robustos de adoecimento ocupacional"),
        ("Relacionamentos",        "2", "Conflitos interpessoais e assédio podem gerar sofrimento psíquico significativo"),
        ("Apoio dos Colegas",      "1", "Isolamento social impacta bem-estar, mas o efeito é predominantemente mediador"),
        ("Apoio da Chefia",        "2", "Falta de suporte gerencial é fator de risco independente para esgotamento"),
        ("Comunicação e Mudanças", "2", "Má gestão de mudanças gera insegurança e queda de engajamento"),
    ]
    for dim_s, nv, just in sev_dados:
        sev_rows.append([
            Paragraph(dim_s, estilo(f"SD{dim_s[:4]}", fontSize=8, fontName="Helvetica-Bold")),
            Paragraph(nv,    estilo(f"SN{nv}{dim_s[:3]}", fontSize=8, alignment=TA_CENTER, fontName="Helvetica-Bold")),
            Paragraph(just,  estilo(f"SJ{dim_s[:4]}", fontSize=8)),
        ])
    sev_tb = Table(sev_rows, colWidths=[4.5*cm, 2.5*cm, 9.7*cm])
    sev_tb.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), AZUL_MEDIO),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, AZUL_CLARO]),
        ("TOPPADDING",    (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("GRID",  (0,0), (-1,-1), 0.3, CINZA_LINHA),
        ("BOX",   (0,0), (-1,-1), 0.5, AZUL_MEDIO),
        ("ALIGN", (0,0), (1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(KeepTogether([sev_titulo, Spacer(1,4), sev_tb]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "* A probabilidade é derivada automaticamente do escore HSE-IT. A severidade e a classificação "
        "final são <b>sugestões orientativas</b> e devem ser revisadas e validadas pelos profissionais "
        "de saúde e segurança do trabalho responsáveis, considerando o histórico de saúde, o contexto "
        "organizacional e outras fontes do PGR (PCMSO, NR-17, CIPA, CATs, afastamentos, etc.).",
        estilo("AstNote", fontSize=7.5, textColor=colors.HexColor("#555555"))))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Indicadores recomendados para monitoramento contínuo:</b>", S_BODY))
    story.append(Spacer(1, 4))
    ind_rows = [[
        Paragraph(h, estilo(f"IH{i}", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white))
        for i, h in enumerate(["Indicador", "Como calcular", "Periodicidade"])
    ]]
    indicadores = [
        ("Taxa de rotatividade", "Desligamentos ÷ total de colaboradores", "Mensal"),
        ("Índice de absenteísmo", "Total horas ausentes ÷ total horas esperadas × 100", "Mensal"),
        ("Afastamentos por transtorno mental", "CID F ou Z relacionados ao trabalho", "Trimestral"),
        ("Afastamentos acidentários", "CATs e afastamentos B91/B92 INSS", "Trimestral"),
        ("Satisfação geral com o trabalho", "Questão extra 36 (média dos respondentes)", "A cada aplicação"),
        ("Autopercepção de saúde", "Questão extra 37 (média dos respondentes)", "A cada aplicação"),
    ]
    for ind in indicadores:
        ind_rows.append([Paragraph(t, estilo(f"IR{hash(t)%9999}", fontSize=8)) for t in ind])
    ind_tb = Table(ind_rows, colWidths=[5*cm, 8.5*cm, 3.2*cm])
    ind_tb.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), AZUL_ESCURO),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, AZUL_CLARO]),
        ("TOPPADDING",    (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("GRID",  (0,0), (-1,-1), 0.3, CINZA_LINHA), ("BOX",   (0,0), (-1,-1), 0.5, AZUL_MEDIO),
    ]))
    story.append(ind_tb)
    story.append(PageBreak())
    story += secao("8. Orientações para Inserção no PGR")
    story.append(Paragraph(
        "Esta seção apresenta orientações objetivas para a incorporação dos riscos psicossociais identificados ao "
        "<b>Programa de Gerenciamento de Riscos (PGR)</b>, "
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
         "matriz de risco do PGR. A conversão depende do formato da matriz adotada pelos "
         "profissionais de saúde e segurança do trabalho:"),
        ("Severidade — julgamento dos profissionais de saúde e segurança do trabalho",
         "A severidade do risco é de julgamento exclusivo dos profissionais de saúde e "
         "segurança do trabalho, considerando o contexto da empresa, o histórico de saúde "
         "dos trabalhadores, a natureza das atividades e outras fontes do PGR (PCMSO, "
         "atestados, afastamentos, NR-17, etc.). Recomenda-se que dimensões com escore "
         "abaixo de 40 sejam discutidas pelos profissionais de saúde e segurança do trabalho "
         "responsáveis antes da classificação final de risco."),
        ("Medidas de controle",
         "As ações do Plano (Seção 7) devem ser transcritas para o campo de "
         "<i>medidas de prevenção e controle</i> do PGR, com responsável, prazo e "
         "forma de monitoramento definidos."),
        ("Monitoramento e revisão",
         "Recomenda-se reaplicação do HSE-IT a cada <b>12 meses</b> ou após mudanças "
         "organizacionais relevantes. Os resultados devem ser comparados ao baseline "
         "deste laudo e registrados como evidência de monitoramento no PGR."),
        ("Documentação e evidências",
         "Mantenha arquivados: este laudo assinado, o formulário aplicado e os registros de "
         "ações implementadas. Esses documentos constituem evidência perante fiscalização do MTE. "
         "Os dados brutos anonimizados — planilha com respostas individuais por item, sem qualquer "
         "campo identificador (nome, matrícula, e-mail, metadados de acesso ou de horário) — "
         "podem ser entregues à organização mediante solicitação formal, desde que: (a) setores "
         "com menos de 5 respondentes sejam suprimidos da planilha; (b) a organização se comprometa "
         "por escrito a não realizar tentativas de reidentificação; e (c) o uso seja restrito a "
         "fins internos de gestão de saúde e segurança. A entrega deve ser documentada e registrada "
         "no arquivo do caso."),
    ]:
        story.append(KeepTogether([
            Paragraph(f"<b>{tit_o}</b>",
                estilo(f"OT{hash(tit_o)%9999}", fontName="Helvetica-Bold",
                       fontSize=9, textColor=AZUL_MEDIO)),
            Paragraph(txt_o, S_BODY), Spacer(1,8),
        ]))

    # Tabela de conversão de escores por tipo de matriz
    story.append(Spacer(1,4))
    def mc(txt, bold=False, center=False, white=False):
        return Paragraph(txt, estilo(f"MC{hash(txt)%9999}", fontSize=8, leading=11,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            textColor=colors.white if white else CINZA_TEXTO,
            alignment=TA_CENTER if center else TA_JUSTIFY))

    matriz_rows = [
        [mc("Matriz",True,True,white=True), mc("Intervalos de escore",True,True,white=True),
         mc("Nível de probabilidade sugerido",True,True,white=True)],
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
        "pelos profissionais de saúde e segurança do trabalho conforme a realidade da organização, podendo ser complementados com "
        "outras fontes do PGR (PCMSO, NR-17, CIPA, etc.).", S_BODY))
    story.append(Spacer(1,8))

    def gro_cell(txt, bold=False, italic=False, white=False):
        fn = "Helvetica-Bold" if bold else "Helvetica-Oblique" if italic else "Helvetica"
        tc = colors.white if white else CINZA_TEXTO
        return Paragraph(txt, estilo(f"GC{hash(txt)%9999}",
            fontSize=7, leading=10, fontName=fn, textColor=tc))

    CINZA_ITER = colors.HexColor("#f0f0f0")
    gro_rows = [[gro_cell(h, bold=True, white=True) for h in
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
         "Esgotamento ocupacional, desmotivação, absenteísmo",
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

    # 2 linhas em branco para os profissionais de saúde e segurança preencherem
    for _ in range(2):
        gro_rows.append([gro_cell("A preencher pelos profissionais de saúde e segurança do trabalho", italic=True)] * 6)

    gro = Table(gro_rows, colWidths=[3*cm, 3.2*cm, 2.8*cm, 3.5*cm, 1.5*cm, 1.7*cm])
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

    # 9. CONSIDERAÇÕES FINAIS
    story.append(Spacer(1, 20))
    story += secao("9. Considerações Finais")
    story.append(Paragraph(
        "Este laudo apresenta os resultados da avaliação dos fatores de risco psicossocial "
        f"realizada em <b>{dados['empresa']}</b> com base no HSE Indicator Tool (HSE-IT), "
        "instrumento validado internacionalmente e adaptado para o contexto brasileiro. "
        "As análises, interpretações e recomendações aqui contidas têm caráter técnico e "
        "orientativo, e não esgotam a complexidade dos fenômenos psicossociais no ambiente "
        "de trabalho.", S_BODY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Os resultados refletem a percepção dos colaboradores no momento da coleta e devem "
        "ser interpretados no contexto organizacional específico da empresa, em conjunto com "
        "outras fontes de informação disponíveis — como dados de afastamentos, rotatividade, "
        "PCMSO e demais programas de saúde e segurança. A responsabilidade pela classificação "
        "final dos riscos, pela definição das medidas de controle e pela incorporação ao PGR "
        "é dos profissionais de saúde e segurança do trabalho da organização.", S_BODY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Recomenda-se a <b>reaplicação periódica do instrumento</b> — idealmente a cada 12 a "
        "24 meses, ou após intervenções organizacionais relevantes — para monitorar a evolução "
        "dos escores e verificar a eficácia das ações implementadas. A comparação longitudinal "
        "dos resultados constitui evidência robusta de gestão ativa e documentada dos riscos "
        "psicossociais perante a fiscalização do MTE.", S_BODY))
    story.append(Spacer(1, 30))

    # 10. ASSINATURAS
    story += secao("10. Responsáveis Técnicos")
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
        "n_minimo": st.session_state.get("n_minimo", 5),
        "q36": st.session_state.get("q36", 0.0),
        "q37": st.session_state.get("q37", 0.0),
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
    if "q36"            in dados: st.session_state["q36"]            = dados["q36"]
    if "q37"            in dados: st.session_state["q37"]            = dados["q37"]
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

    st.markdown('<div class="section-header">Indicadores de Desfecho (Q36 e Q37)</div>', unsafe_allow_html=True)
    st.caption("Informe a média das respostas coletadas. Escala: 1 = Muito ruim / 2 = Ruim / 3 = Razoável / 4 = Bom / 5 = Muito bom")
    cq1, cq2 = st.columns(2)
    st.session_state.q36 = cq1.number_input(
        "Q36 — Satisfação geral com o trabalho (média)",
        min_value=0.0, max_value=5.0, step=0.1,
        value=float(st.session_state.q36),
        format="%.1f",
        help="De maneira geral, pensando no seu trabalho, quão satisfeito você está com ele como um todo?"
    )
    st.session_state.q37 = cq2.number_input(
        "Q37 — Autopercepção de saúde (média)",
        min_value=0.0, max_value=5.0, step=0.1,
        value=float(st.session_state.q37),
        format="%.1f",
        help="Em geral, sente que a sua saúde é:"
    )
    if st.session_state.q36 > 0 or st.session_state.q37 > 0:
        def media_para_pct(v):
            if v <= 0: return 0.0
            return round((v - 1) / 4 * 100, 1)
        def interp_desfecho(v):
            if v == 0: return "—"
            if v <= 2: return "Desfavorável"
            if v <= 3: return "Neutro"
            return "Favorável"
        p36 = media_para_pct(st.session_state.q36)
        p37 = media_para_pct(st.session_state.q37)
        st.markdown(
            f'<div class="info-box">'
            f'Q36: média <b>{st.session_state.q36:.1f}</b> → <b>{p36:.0f}%</b> ({interp_desfecho(st.session_state.q36)}) &nbsp;|&nbsp; '
            f'Q37: média <b>{st.session_state.q37:.1f}</b> → <b>{p37:.0f}%</b> ({interp_desfecho(st.session_state.q37)})'
            f'</div>',
            unsafe_allow_html=True
        )

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
    st.markdown('<div class="alert-box">⚠️ Os textos abaixo foram gerados automaticamente com base nos escores. Revise e edite antes de gerar o PDF.</div>', unsafe_allow_html=True)
    for dim in DIMENSOES:
        val = st.session_state.escores.get(dim, 65)
        if val <= 20:   cor = "🔴"
        elif val <= 40: cor = "🟠"
        elif val <= 60: cor = "🟡"
        elif val <= 80: cor = "🟢"
        else:           cor = "✅"
        # Usar texto automático como default se campo ainda estiver vazio
        texto_atual = st.session_state.interpretacoes.get(dim, "")
        texto_default = texto_atual if texto_atual else texto_automatico(dim, val)
        txt = st.text_area(
            f"{cor} **{dim}** — Escore: {val} ({label_escore(val)})",
            texto_default,
            height=120, key=f"interp_{dim}"
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
    st.markdown('<div class="info-box">💡 O plano abaixo foi gerado automaticamente com base nos escores das dimensões. Edite, remova ou acrescente ações conforme necessário.</div>', unsafe_allow_html=True)

    # Gerar plano automático se ainda estiver vazio
    if not st.session_state.plano:
        plano_auto = []
        prior_map = {True: "Alta", False: "Média"}  # crítico/ruim → Alta; médio → Média
        for dim in DIMENSOES:
            val = st.session_state.escores.get(dim, 65)
            if val > 60:
                continue  # bom/excelente: só 1 ação de monitoramento
            acoes_list = acoes_automaticas(dim, val)
            prior = "Alta" if val <= 40 else "Média"
            for acao in acoes_list:
                plano_auto.append({"dim": dim, "prior": prior, "acao": acao, "resp": "", "prazo": ""})
        # Adicionar monitoramento para dimensões boas/excelentes
        for dim in DIMENSOES:
            val = st.session_state.escores.get(dim, 65)
            if val > 60:
                acoes_list = acoes_automaticas(dim, val)
                for acao in acoes_list:
                    plano_auto.append({"dim": dim, "prior": "Baixa", "acao": acao, "resp": "", "prazo": ""})
        st.session_state.plano = plano_auto

    n_acoes = st.number_input("Quantas ações deseja incluir?", 0, 50,
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
                "q36":            st.session_state.q36,
                "q37":            st.session_state.q37,
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
