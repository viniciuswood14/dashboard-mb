import streamlit as st
import pandas as pd
from orcamentobr import despesa_detalhada
import numpy as np

# --- 1. Configuração da Página e Título ---
st.set_page_config(page_title="Execução PAC - Marinha", layout="wide")
st.title("Execução do Novo PAC - MB")

# --- 2. Mapeamento dos Programas e Ações ---
PROGRAMAS_ACOES = {
    'PROSUB': {
        '123G': 'IMPLANTACAO DE ESTALEIRO E BASE NAVAL PARA CONSTRUCAO E MANUTENCAO',
        '123H': 'CONSTRUCAO DE SUBMARINO DE PROPULSAO NUCLEAR',
        '123I': 'CONSTRUCAO DE SUBMARINOS CONVENCIONAIS'
    },
    'PNM': {
        '14T7': 'DESENVOLVIMENTO DE SISTEMAS DE TECNOLOGIA NUCLEAR DA MARINHA'
    },
    'PRONAPA': {
        '1N47': 'CONSTRUCAO DE NAVIOS-PATRULHA DE 500 TONELADAS (NPA 500T)'
    }
}

# --- 3. Função Cacheada para buscar os dados TOTAIS por Ação ---
@st.cache_data
def buscar_dados_acao(ano, acao_cod):
    """
    Busca os dados de UMA ação, totalizados (sem agrupar por GND, Fonte, etc.)
    """
    print(f"Buscando DADOS TOTAIS para {ano}, Ação {acao_cod}...")
    try:
        df = despesa_detalhada(
            exercicio=ano,
            acao=acao_cod,
            acao=True, # Agrupa pela ação para obter uma linha de total
            inclui_descricoes=True,
            ignore_secure_certificate=True
        )
        # A API retorna: loa, loa_mais_credito, empenhado, liquidado, pago
        return df.iloc[0] if not df.empty else None
    except Exception as e:
        st.error(f"Erro ao consultar o SIOP para a ação {acao_cod}: {e}")
        return None

# --- 4. Função de Estilo para o DataFrame ---
def style_rows(row):
    """Aplica estilo de 'Agrupador' ou 'Total' no DataFrame"""
    style = ''
    if pd.isna(row['AÇÃO']) and row['PROGRAMA'] == 'Total Geral':
        # Linha de Total Geral
        style = 'background-color: #002060; color: white; font-weight: bold;'
    elif pd.isna(row['AÇÃO']):
        # Linha de Programa (PROSUB, PNM, etc.)
        style = 'background-color: #DDEBF7; font-weight: bold;'
    
    return [style] * len(row)

# --- 5. Interface do Usuário (Barra Lateral) ---
st.sidebar.header("Filtros")
ano_selecionado = st.sidebar.number_input(
    "Selecione o Ano", 
    min_value=2010, 
    max_value=2025, 
    value=2024
)

# --- 6. Lógica Principal do Dashboard ---
if st.sidebar.button("Consultar"):
    
    all_data = []
    status_text = st.empty() 

    # --- 6.1. Loop de Busca ---
    for programa, acoes in PROGRAMAS_ACOES.items():
        for acao_cod, acao_desc in acoes.items():
            status_text.info(f"Consultando {programa} - {acao_cod}...")
            dados_linha = buscar_dados_acao(ano_selecionado, acao_cod)
            
            if dados_linha is not None:
                dados_linha['PROGRAMA_NOME'] = programa
                dados_linha['ACAO_DESC_MANUAL'] = f"{acao_cod} - {acao_desc.upper()}"
                all_data.append(dados_linha)

    status_text.success("Consulta concluída! Gerando tabela...")
    
    if all_data:
        dados_brutos = pd.DataFrame(all_data)
        
        # --- 6.2. Processamento e Agrupamento ---
        display_list = []
        
        for programa, acoes in PROGRAMAS_ACOES.items():
            df_programa = dados_brutos[dados_brutos['PROGRAMA_NOME'] == programa]
            
            if not df_programa.empty:
                # 1. Linha de Sumário do Programa
                display_list.append({
                    'PROGRAMA': programa,
                    'AÇÃO': np.nan,
                    'LOA': df_programa['loa'].sum(),                 # ADICIONADO
                    'DOTAÇÃO ATUAL': df_programa['loa_mais_credito'].sum(),
                    'EMPENHADO (c)': df_programa['empenhado'].sum(),
                    'LIQUIDADO': df_programa['liquidado'].sum(), 
                    'PAGO': df_programa['pago'].sum()               
                })
                
                # 2. Linhas de Ação
                for acao_cod in acoes.keys():
                    df_acao = df_programa[df_programa['Acao_cod'] == acao_cod]
                    if not df_acao.empty:
                        row = df_acao.iloc[0]
                        display_list.append({
                            'PROGRAMA': np.nan,
                            'AÇÃO': row['ACAO_DESC_MANUAL'],
                            'LOA': row['loa'],                     # ADICIONADO
                            'DOTAÇÃO ATUAL': row['loa_mais_credito'],
                            'EMPENHADO (c)': row['empenhado'],
                            'LIQUIDADO': row['liquidado'], 
                            'PAGO': row['pago']               
                        })

        # 3. Linha de Total Geral
        display_list.append({
            'PROGRAMA': 'Total Geral',
            'AÇÃO': np.nan,
            'LOA': dados_brutos['loa'].sum(),                         # ADICIONADO
            'DOTAÇÃO ATUAL': dados_brutos['loa_mais_credito'].sum(),
            'EMPENHADO (c)': dados_brutos['empenhado'].sum(),
            'LIQUIDADO': dados_brutos['liquidado'].sum(), 
            'PAGO': dados_brutos['pago'].sum()               
        })
        
        # --- 6.3. Cria e Formata o DataFrame Final ---
        df_display = pd.DataFrame(display_list)
        
        # Calcula a coluna de percentual
        df_display['% EMP/DOT'] = (
            df_display['EMPENHADO (c)'] / df_display['DOTAÇÃO ATUAL']
        ).replace([np.inf, -np.inf], 0)

        # Reordena colunas
        df_display = df_display[[
            'PROGRAMA', 
            'AÇÃO', 
            'LOA',                  # ADICIONADO
            'DOTAÇÃO ATUAL', 
            'EMPENHADO (c)', 
            'LIQUIDADO',            
            'PAGO',                 
            '% EMP/DOT'
        ]]
        
        st.subheader(f"Execução Orçamentária por Programa (Ano: {ano_selecionado})")
        
        # --- 6.4. Exibe o DataFrame com Estilo ---
        st.dataframe(
            df_display.style
                .apply(style_rows, axis=1) # Aplica o estilo de cor
                .format({
                    'LOA': "R$ {:,.2f}",              # ADICIONADO
                    'DOTAÇÃO ATUAL': "R$ {:,.2f}",
                    'EMPENHADO (c)': "R$ {:,.2f}",
                    'LIQUIDADO': "R$ {:,.2f}",     
                    'PAGO': "R$ {:,.2f}",          
                    '% EMP/DOT': "{:,.1%}"
                })
                .hide(axis="index"), # Esconde o índice (0, 1, 2...)
            use_container_width=True,
            height=(len(df_display) + 1) * 35  # Ajusta a altura dinamicamente
        )

        st.divider()
        st.subheader("Dados Brutos Consolidados (Totais por Ação)")
        # Mostra as colunas relevantes nos dados brutos
        cols_brutas = [
            'PROGRAMA_NOME', 'ACAO_DESC_MANUAL', 'loa', 'loa_mais_credito', 
            'empenhado', 'liquidado', 'pago'
        ]
        st.dataframe(dados_brutos[cols_brutas])
        
        status_text.empty()

    else:
        st.warning(f"Nenhum dado encontrado para estas ações em {ano_selecionado}.")
        status_text.empty()
else:
    st.info("Por favor, selecione o ano na barra lateral e clique em 'Consultar'.")
