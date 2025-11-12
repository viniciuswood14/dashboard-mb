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
#
# ***** ESTA É A FUNÇÃO CORRIGIDA *****
#
@st.cache_data
def buscar_dados_acao(ano, acao_cod):
    """
    Busca os dados de UMA ação, totalizados.
    Corrige o erro de "keyword argument repeated".
    """
    print(f"Buscando DADOS DETALHADOS para {ano}, Ação {acao_cod}...")
    try:
        # 1. Busca os dados detalhados (sem agrupar, o que retorna múltiplas linhas)
        df_detalhado = despesa_detalhada(
            exercicio=ano,
            acao=acao_cod, # <-- Este é o FILTRO (ex: '123G')
            # acao=True,   <-- Esta linha causava o ERRO e foi REMOVIDA
            inclui_descricoes=True,
            ignore_secure_certificate=True
        )
        
        if df_detalhado.empty:
            return None
            
        # 2. Soma os valores para obter o TOTAL da ação
        # Seleciona apenas as colunas numéricas que nos interessam
        colunas_numericas = ['loa', 'loa_mais_credito', 'empenhado', 'liquidado', 'pago']
        
        # Garante que as colunas existem antes de somar
        colunas_para_somar = [col for col in colunas_numericas if col in df_detalhado.columns]
        
        if not colunas_para_somar:
            return None
            
        # .sum() cria uma "Series" (basicamente uma linha de totais)
        totais_acao = df_detalhado[colunas_para_somar].sum()
        
        # 3. Adiciona as descrições (pega da primeira linha dos dados detalhados)
        # Precisamos do Acao_cod para a lógica de merge depois
        totais_acao['Acao_cod'] = acao_cod 
        if 'Acao_desc' in df_detalhado.columns:
             totais_acao['Acao_desc'] = df_detalhado.iloc[0]['Acao_desc']
        
        # Retorna a "Series" (linha) com os totais
        return totais_acao 

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
                # Adiciona o nome do Programa e a Descrição manual
                dados_linha['PROGRAMA_NOME'] = programa
                dados_linha['ACAO_DESC_MANUAL'] = f"{acao_cod} - {acao_desc.upper()}"
                all_data.append(dados_linha)

    status_text.success("Consulta concluída! Gerando tabela...")
    
    if all_data:
        # Converte a lista de "Series" (linhas) em um DataFrame
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
                    'LOA': df_programa['loa'].sum(),
                    'DOTAÇÃO ATUAL': df_programa['loa_mais_credito'].sum(),
                    'EMPENHADO (c)': df_programa['empenhado'].sum(),
                    'LIQUIDADO': df_programa['liquidado'].sum(), 
                    'PAGO': df_programa['pago'].sum()               
                })
                
                # 2. Linhas de Ação
                for aco_cod_loop in acoes.keys():
                    # Usa o Acao_cod que adicionamos na função
                    df_acao = df_programa[df_programa['Acao_cod'] == aco_cod_loop]
                    if not df_acao.empty:
                        row = df_acao.iloc[0]
                        display_list.append({
                            'PROGRAMA': np.nan,
                            'AÇÃO': row['ACAO_DESC_MANUAL'],
                            'LOA': row['loa'],
                            'DOTAÇÃO ATUAL': row['loa_mais_credito'],
                            'EMPENHADO (c)': row['empenhado'],
                            'LIQUIDADO': row['liquidado'], 
                            'PAGO': row['pago']               
                        })

        # 3. Linha de Total Geral
        display_list.append({
            'PROGRAMA': 'Total Geral',
            'AÇÃO': np.nan,
            'LOA': dados_brutos['loa'].sum(),
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
        ).replace([np.inf, -np.inf, np.nan], 0) # Adicionado .replace(np.nan, 0) por segurança

        # Reordena colunas
        df_display = df_display[[
            'PROGRAMA', 
            'AÇÃO', 
            'LOA',
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
                    'LOA': "R$ {:,.2f}",
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
            'PROGRAMA_NOME', 'ACAO_DESC_MANUAL', 'Acao_cod', 'loa', 'loa_mais_credito', 
            'empenhado', 'liquidado', 'pago'
        ]
        # Filtra para mostrar apenas colunas que realmente existem
        st.dataframe(dados_brutos[[c for c in cols_brutas if c in dados_brutos.columns]])
        
        status_text.empty()

    else:
        st.warning(f"Nenhum dado encontrado para estas ações em {ano_selecionado}.")
        status_text.empty()
else:
    st.info("Por favor, selecione o ano na barra lateral e clique em 'Consultar'.")
