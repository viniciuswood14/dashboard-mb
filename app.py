import streamlit as st
import pandas as pd
from orcamentobr import despesa_detalhada
import locale

# --- 1. Configuração da Página e Título ---
st.set_page_config(page_title="Projetos Marinha - PAC", layout="wide")
st.title("Projetos Estratégicos da Marinha - Novo PAC")

# --- Mapeamento das Ações de Interesse ---
ACOES_DICT = {
    '14T7': 'Tecnologia Nuclear da Marinha (PNM)',
    '123G': 'Implantação Estaleiro/Base Naval (PROSUB-Infra)',
    '123H': 'Construção Submarino Nuclear (PROSUB-SNBR)',
    '123I': 'Construção Submarinos Convencionais (PROSUB-SBR)',
    '1N47': 'Construção Navios-Patrulha 500t (NPa 500t)'
}

# --- Listas para os filtros ---
ACOES_DISPLAY_LIST = [f"{cod} - {desc}" for cod, desc in ACOES_DICT.items()]
OPTIONS_LIST = ['Selecionar Todas'] + ACOES_DISPLAY_LIST

# --- Função para formatar números como Moeda ---
def formatar_moeda(valor):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(valor, grouping=True)
    except:
        return f"R$ {valor:,.2f}"

# --- Função Cacheada para buscar os dados ---
# 
# ***** ESTA É A FUNÇÃO CORRIGIDA *****
#
@st.cache_data
def buscar_dados(ano, acao_cod):
    print(f"Buscando dados para {ano}, Ação {acao_cod}...")
    try:
        df = despesa_detalhada(
            exercicio=ano,
            acao=acao_cod,
            
            # --- CORREÇÃO AQUI ---
            # Pedimos explicitamente para agrupar por estas colunas:
            gnd=True,
            fonte=True,
            uo=True,
            # ---------------------

            inclui_descricoes=True,
            ignore_secure_certificate=True
        )
        return df
    except Exception as e:
        st.error(f"Erro ao consultar o SIOP para a ação {acao_cod}: {e}")
        return pd.DataFrame()

# --- Interface do Usuário (Barra Lateral) ---
st.sidebar.header("Filtros")
ano_selecionado = st.sidebar.number_input("Selecione o Ano", min_value=2010, max_value=2025, value=2024)

selecoes_usuario = st.sidebar.multiselect(
    "Selecione a(s) Ação(ões)", 
    options=OPTIONS_LIST
)

# --- Lógica Principal do Dashboard ---
if st.sidebar.button("Consultar"):
    
    # Lógica para "Selecionar Todas"
    codes_to_process = []
    if 'Selecionar Todas' in selecoes_usuario:
        codes_to_process = list(ACOES_DICT.keys())
    else:
        codes_to_process = [opt.split(' - ')[0] for opt in selecoes_usuario]

    if not codes_to_process:
        st.warning("Por favor, selecione uma ou mais ações e clique em 'Consultar'.")
    else:
        # Loop para buscar dados de MÚLTIPLAS ações
        all_data = []
        status_text = st.empty() 

        for i, code in enumerate(codes_to_process):
            desc_loop = ACOES_DICT.get(code, code)
            status_text.info(f"Consultando {i+1}/{len(codes_to_process)}: {desc_loop}...")
            
            dados_acao = buscar_dados(ano_selecionado, code)
            all_data.append(dados_acao)

        status_text.success("Consulta concluída! Gerando análises...")
        
        dados = pd.concat(all_data, ignore_index=True)
        
        if not dados.empty:
            
            # --- SEÇÃO 1: VISÃO GERAL ---
            st.subheader(f"Visão Geral Consolidada (Ano: {ano_selecionado})")
            
            dotacao_atualizada = dados['loa_mais_credito'].sum()
            empenhado = dados['empenhado'].sum()
            liquidado = dados['liquidado'].sum()
            pago = dados['pago'].sum()

            col_metrica1, col_metrica2, col_metrica3, col_metrica4 = st.columns(4)
            col_metrica1.metric("Dotação Atualizada", formatar_moeda(dotacao_atualizada))
            col_metrica2.metric("Empenhado", formatar_moeda(empenhado))
            col_metrica3.metric("Liquidado", formatar_moeda(liquidado))
            col_metrica4.metric("Pago", formatar_moeda(pago))

            dados_grafico_total = pd.DataFrame({
                'Valores': [dotacao_atualizada, empenhado, liquidado, pago],
                'Etapa': ['1. Dotação Atualizada', '2. Empenhado', '3. Liquidado', '4. Pago']
            })
            st.bar_chart(dados_grafico_total, x='Etapa', y='Valores', height=300)
            
            st.divider()

            # --- SEÇÃO 2: ANÁLISES (GND e Fonte) ---
            st.subheader("Análise Detalhada dos Gastos")
            col_analise1, col_analise2 = st.columns(2)

            # --- 2.1 Análise por GND ---
            # Esta secção irá agora funcionar
            with col_analise1:
                st.markdown("#### Execução por Natureza de Despesa (GND)")
                gnd_data = dados.groupby(['GND_cod', 'GND_desc'])['empenhado'].sum().reset_index()
                gnd_data = gnd_data[gnd_data['empenhado'] > 0].sort_values('empenhado', ascending=False)
                gnd_data['display'] = gnd_data['GND_cod'] + ' - ' + gnd_data['GND_desc']
                st.bar_chart(gnd_data, x='display', y='empenhado')

            # --- 2.2 Análise por Fonte de Recursos ---
            # Esta secção também irá funcionar
            with col_analise2:
                st.markdown("#### Execução por Fonte de Recursos (Top 10)")
                fonte_data = dados.groupby(['Fonte_cod', 'Fonte_desc'])['empenhado'].sum().reset_index()
                fonte_data = fonte_data[fonte_data['empenhado'] > 0].sort_values('empenhado', ascending=False).head(10)
                fonte_data['display'] = fonte_data['Fonte_cod'] + ' - ' + fonte_data['Fonte_desc']
                st.bar_chart(fonte_data, x='display', y='empenhado')
            
            st.divider()

            # --- SEÇÃO 3: ANÁLISE POR UNIDADE ORÇAMENTÁRIA (UO) ---
            st.subheader("Quem está Executando (Top 10 UOs)")
            st.markdown("Mostra as Unidades Orçamentárias que mais empenharam recursos para as ações selecionadas.")
            
            # Esta secção também irá funcionar
            uo_data = dados.groupby(['UO_cod', 'UO_desc'])['empenhado'].sum().reset_index()
            uo_data = uo_data[uo_data['empenhado'] > 0].sort_values('empenhado', ascending=False).head(10)
            uo_data['display'] = uo_data['UO_cod'] + ' - ' + uo_data['UO_desc']
            st.bar_chart(uo_data, x='display', y='empenhado')

            st.divider()

            # --- SEÇÃO 4: DADOS BRUTOS ---
            st.subheader(f"Detalhamento dos Dados ({len(dados)} linhas)")
            st.dataframe(dados)
            
            status_text.empty()

        else:
            st.warning(f"Nenhum dado encontrado para estas ações em {ano_selecionado}.")
            status_text.empty()
else:
    st.info("Por favor, selecione os filtros na barra lateral e clique em 'Consultar'.")
