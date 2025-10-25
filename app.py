import streamlit as st
import pandas as pd
from orcamentobr import despesa_detalhada
import locale

# --- Configuração da Página ---
st.set_page_config(page_title="Dashboard Ações MB", layout="wide")
st.title("Dashboard Orçamentário - Ações Estratégicas da Marinha")

# --- Mapeamento das Ações de Interesse ---
# (Com base nos códigos que forneceu e pesquisa pública)
ACOES_DICT = {
    '14T7': 'Tecnologia Nuclear da Marinha (PNM)',
    '123G': 'Implantação Estaleiro/Base Naval (PROSUB-Infra)',
    '123H': 'Construção Submarino Nuclear (PROSUB-SNBR)',
    '123I': 'Construção Submarinos Convencionais (PROSUB-SBR)',
    '1N47': 'Construção Navios-Patrulha 500t (NPa 500t)'
}
# Lista de descrições para o usuário selecionar
lista_descricoes = list(ACOES_DICT.values())

# --- Função para formatar números como Moeda ---
def formatar_moeda(valor):
    try:
        # Tenta usar o locale Brasileiro para formatar
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(valor, grouping=True)
    except:
        # Se falhar (comum em servidores), usa uma formatação simples
        return f"R$ {valor:,.2f}"

# --- Função Cacheada para buscar os dados ---
# O @st.cache_data guarda o resultado e só executa de novo
# se os parâmetros (ano, acao_cod) mudarem.
@st.cache_data
def buscar_dados(ano, acao_cod):
    print(f"Buscando dados para {ano} e {acao_cod}...")
    try:
        df = despesa_detalhada(
            exercicio=ano,
            acao=acao_cod,
            inclui_descricoes=True,
            ignore_secure_certificate=True  # Usando a correção de SSL
        )
        return df
    except Exception as e:
        st.error(f"Erro ao consultar a API do SIOP: {e}")
        return pd.DataFrame()

# --- Interface do Usuário (Barra Lateral) ---
st.sidebar.header("Filtros")
ano_selecionado = st.sidebar.number_input("Selecione o Ano", min_value=2010, max_value=2025, value=2024)
acao_descricao = st.sidebar.selectbox("Selecione a Ação", options=lista_descricoes)

# Encontrar o código da ação a partir da descrição
acao_cod_selecionado = [cod for cod, desc in ACOES_DICT.items() if desc == acao_descricao][0]


# --- Lógica Principal do Dashboard ---
if st.sidebar.button("Consultar"):
    
    with st.spinner(f"Consultando dados para '{acao_descricao}' no ano de {ano_selecionado}... Isso pode levar um minuto."):
        
        dados = buscar_dados(ano_selecionado, acao_cod_selecionado)
        
        if not dados.empty:
            st.subheader(f"Resultados para: {acao_descricao} ({acao_cod_selecionado})")
            
            # --- 1. Métricas Principais ---
            # Soma os valores, já que a consulta pode retornar várias linhas (ex: por GND, Fonte)
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

            # --- 2. Gráfico de Execução ---
            st.markdown("### Gráfico da Execução")
            
            # Prepara os dados para o gráfico
            dados_grafico = pd.DataFrame({
                'Valores': [dotacao_atualizada, empenhado, liquidado, pago],
                'Etapa': ['1. Dotação Atualizada', '2. Empenhado', '3. Liquidado', '4. Pago']
            })
            
            st.bar_chart(dados_grafico, x='Etapa', y='Valores')

            # --- 3. Tabela de Dados Detalhada ---
            st.markdown(f"### Detalhamento dos Dados ({len(dados)} linhas)")
            # Mostra a tabela completa (o dataframe)
            st.dataframe(dados)

        else:
            st.warning("Nenhum dado encontrado para esta combinação de ano e ação.")

else:
    st.info("Por favor, selecione os filtros na barra lateral e clique em 'Consultar'.")
