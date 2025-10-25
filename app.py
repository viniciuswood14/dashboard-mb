import streamlit as st
import pandas as pd
from orcamentobr import despesa_detalhada
import locale

# --- 1. Configuração da Página e Novo Título ---
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

# --- 2. Criar lista formatada (Código + Descrição) ---
ACOES_DISPLAY_LIST = [f"{cod} - {desc}" for cod, desc in ACOES_DICT.items()]

# --- 3. Criar lista de opções com "Selecionar Todas" ---
OPTIONS_LIST = ['Selecionar Todas'] + ACOES_DISPLAY_LIST

# --- Função para formatar números como Moeda ---
def formatar_moeda(valor):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(valor, grouping=True)
    except:
        return f"R$ {valor:,.2f}"

# --- Função Cacheada para buscar os dados ---
# O cache continua a funcionar por ação individual, o que é ótimo
@st.cache_data
def buscar_dados(ano, acao_cod):
    print(f"Buscando dados para {ano} e {acao_cod}...")
    try:
        df = despesa_detalhada(
            exercicio=ano,
            acao=acao_cod,
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

# --- 3. Mudar para st.multiselect ---
selecoes_usuario = st.sidebar.multiselect(
    "Selecione a(s) Ação(ões)", 
    options=OPTIONS_LIST
)

# --- Lógica Principal do Dashboard ---
if st.sidebar.button("Consultar"):
    
    # --- 3. Lógica para "Selecionar Todas" ---
    codes_to_process = []
    if 'Selecionar Todas' in selecoes_usuario:
        codes_to_process = list(ACOES_DICT.keys())
    else:
        # Extrai apenas o código (ex: '14T7') da string formatada
        codes_to_process = [opt.split(' - ')[0] for opt in selecoes_usuario]

    if not codes_to_process:
        st.warning("Por favor, selecione uma ou mais ações e clique em 'Consultar'.")
    else:
        # --- Loop para buscar dados de MÚLTIPLAS ações ---
        all_data = []
        status_text = st.empty() # Para mostrar o progresso

        for i, code in enumerate(codes_to_process):
            desc_loop = ACOES_DICT.get(code, code) # Pega a descrição para o status
            status_text.info(f"Consultando {i+1}/{len(codes_to_process)}: {desc_loop}...")
            
            dados_acao = buscar_dados(ano_selecionado, code)
            all_data.append(dados_acao)

        status_text.success("Consulta concluída! Consolidando dados...")
        
        # Consolida todos os dataframes numa única tabela
        dados = pd.concat(all_data, ignore_index=True)
        
        if not dados.empty:
            st.subheader(f"Resultados Consolidados para o Ano: {ano_selecionado}")
            
            # --- 1. Métricas Principais (agora somam todas as ações selecionadas) ---
            dotacao_atualizada = dados['loa_mais_credito'].sum()
            empenhado = dados['empenhado'].sum()
            liquidado = dados['liquidado'].sum()
            pago = dados['pago'].sum()

            st.markdown("### Execução Orçamentária Total")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Dotação Atualizada", formatar_moeda(dotacao_atualizada))
            col2.metric("Empenhado", formatar_moeda(empenhado))
            col3.metric("Liquidado", formatar_moeda(liquidado))
            col4.metric("Pago", formatar_moeda(pago))

            # --- 2. Gráfico de Execução (Consolidado) ---
            st.markdown("### Gráfico da Execução (Consolidado)")
            dados_grafico = pd.DataFrame({
                'Valores': [dotacao_atualizada, empenhado, liquidado, pago],
                'Etapa': ['1. Dotação Atualizada', '2. Empenhado', '3. Liquidado', '4. Pago']
            })
            st.bar_chart(dados_grafico, x='Etapa', y='Valores')

            # --- 3. Tabela de Dados Detalhada (Consolidada) ---
            st.markdown(f"### Detalhamento dos Dados ({len(dados)} linhas)")
            st.dataframe(dados)
            
            # Limpa o status
            status_text.empty()

        else:
            st.warning("Nenhum dado encontrado para esta combinação de ano e ações.")
            status_text.empty()
else:
    st.info("Por favor, selecione os filtros na barra lateral e clique em 'Consultar'.")
