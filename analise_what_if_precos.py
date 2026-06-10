import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt

# configuração da página do dashboard para ocupar a tela toda
st.set_page_config(page_title="SAD - Precificação Amazon", layout="wide")

st.title("📊 Sistema de Apoio à Decisão (SAD) - Precificação Tática")
st.markdown("Interface interativa baseada no processamento de dados do e-commerce.")

print("A carregar os dados do amazon.csv...")
try:
    df = pd.read_csv('amazon.csv')
    print("Ficheiro da Amazon carregado com sucesso!")
except FileNotFoundError:
    print("ERRO: O ficheiro 'amazon.csv' não foi encontrado na pasta.")
    st.error("ERRO: O ficheiro 'amazon.csv' não foi encontrado na pasta.")
    st.stop()

# limpeza dos dados: remover o símbolo '₹' (rupia) e converter preços para float
def limpar_preco(valor):
    if pd.isna(valor): return 0.0
    return float(str(valor).replace('₹', '').replace(',', '').strip())

df['Preco_Original'] = df['actual_price'].apply(limpar_preco)

# como a coluna category tem subcategorias longas separadas por '|',
# vamos extrair apenas o primeiro nome para termos categorias limpas.
df['Categoria_Principal'] = df['category'].apply(lambda x: str(x).split('|')[0] if pd.notna(x) else 'Outros')

# filtrar o volume de demanda (remover vírgulas do rating_count)
df['Demanda_Base'] = df['rating_count'].astype(str).str.replace(',', '').str.strip()
df['Demanda_Base'] = pd.to_numeric(df['Demanda_Base'], errors='coerce').fillna(100)

# agrupamos por categoria principal para extrair a média de preço real e volume real
df_base = df.groupby('Categoria_Principal').agg(
    Preco_Original=('Preco_Original', 'mean'),
    Quantidade_Base=('Demanda_Base', 'sum')
).reset_index()

# selecionamos as 3 categorias com maior volume para o estudo ficar focado e limpo
df_base = df_base.sort_values(by='Quantidade_Base', ascending=False).head(3).copy()

st.sidebar.header("⚙️ Parâmetros das Regras de Negócio")
st.sidebar.markdown("Arraste os controles abaixo para reconfigurar as variáveis do SAD ao vivo:")

# injetando as variáveis do sad (margens e elasticidades)
# como a base não traz margem nem elasticidade, o sad injeta estas premissas por sliders:
premissas_dinamicas = {}
for idx, row in df_base.iterrows():
    cat = row['Categoria_Principal']
    st.sidebar.subheader(f"📁 {cat}")
    
    # valores padrão originais do teu script para servir de início
    margem_padrao = 0.40 if "Electronics" in cat else (0.45 if "Computers" in cat else 0.35)
    eps_padrao = -2.5 if "Electronics" in cat else (-1.4 if "Computers" in cat else -0.8)
    
    # sliders interativos para o gestor brincar com os números
    margem = st.sidebar.slider(f"Margem de Lucro Base ({cat})", 0.10, 0.80, margem_padrao, 0.05)
    elasticidade = st.sidebar.slider(f"Elasticidade-Preço ({cat})", -5.0, -0.1, eps_padrao, 0.1)
    
    premissas_dinamicas[cat] = {'margem': margem, 'eps': elasticidade}

# motor analítico what-if (simulação de cenários)
politicas_desconto = [0.00, 0.05, 0.10, 0.15, 0.20] # políticas a testar: 0% a 20%
resultados_simulacao = []

for dct in politicas_desconto:
    for idx, row in df_base.iterrows():
        cat = row['Categoria_Principal']
        p0 = row['Preco_Original']
        q0 = row['Quantidade_Base']
        
        # puxa os dados ajustados dinamicamente nos controles laterais da tela
        margem_atual = premissas_dinamicas[cat]['margem']
        eps_atual = premissas_dinamicas[cat]['eps']
        
        # calcula o custo unitário fixo com base nos preços reais extraídos da amazon
        custo = p0 * (1 - margem_atual)
        
        # projeções do que aconteceria (what-if)
        p_novo = p0 * (1 - dct)
        q_nova = int(q0 * (1 - (eps_atual * dct))) # modelo matemático da elasticidade-preço
        receita_nova = p_novo * q_nova
        lucro_novo = (p_novo - custo) * q_nova
        
        resultados_simulacao.append({
            'Cenário Desconto': f"{int(dct*100)}%",
            'Categoria': cat,
            'Preço Médio ($)': round(p_novo, 2),
            'Demanda Projetada (Uds)': q_nova,
            'Lucro Estimado ($)': round(lucro_novo, 2)
        })

df_what_if = pd.DataFrame(resultados_simulacao)

# geração automática do arquivo png para o latex em segundo plano
plt.figure(figsize=(10, 5))
for cat in df_base['Categoria_Principal']:
    dados_cat = df_what_if[df_what_if['Categoria'] == cat]
    plt.plot(dados_cat['Cenário Desconto'], dados_cat['Lucro Estimado ($)'], marker='o', linewidth=2, label=cat)

plt.title('Análise What-If: Impacto dos Descontos no Lucro (Base Amazon)', fontsize=12, fontweight='bold', color='black')
plt.xlabel('Cenários de Desconto Concedido', color='black')
plt.ylabel('Lucro Líquido Projetado ($)', color='black')
plt.xticks(color='black')
plt.yticks(color='black')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig('grafico_what_if_amazon.png', dpi=300)
plt.close() # fecha o gráfico para não consumir memória do servidor

# tomada de decisão automatizada
lucro_por_cenario = df_what_if.groupby('Cenário Desconto')['Lucro Estimado ($)'].sum()
melhor_cenario = lucro_por_cenario.idxmax()
maior_lucro = lucro_por_cenario.max()

# bloco de cartões com os outputs de recomendação e lucro máximo
col1, col2 = st.columns(2)
with col1:
    st.metric(label="💡 RECOMENDAÇÃO AUTOMÁTICA DO SAD", value=f"Política de {melhor_cenario} de desconto.")
with col2:
    st.metric(label="💰 Lucro Consolidado Projetado", value=f"$ {maior_lucro:,.2f}")

st.markdown("---")

# visualização dos dados (gráfico dinâmico do plotly que substitui o matplotlib antigo)
fig = px.line(
    df_what_if, 
    x='Cenário Desconto', 
    y='Lucro Estimado ($)', 
    color='Categoria',
    markers=True,
    labels={'Lucro Estimado ($)': 'Lucro Líquido Projetado ($)', 'Cenário Desconto': 'Cenários de Desconto Concedido'},
    title="Análise What-If: Impacto dos Descontos no Lucro (Base Amazon)"
)

# estilização para garantir que todas as letras fiquem pretas e legíveis
fig.update_layout(
    hovermode="x unified", 
    template="plotly_white",
    title={
        'font': {'size': 16, 'family': 'sans-serif', 'color': 'white'},
        'y': 0.95,
        'x': 0.5,
        'xanchor': 'center',
        'yanchor': 'top'
    },
    font=dict(
        family="sans-serif", 
        size=12, 
        color="white"
    ),
    xaxis=dict(
        title_font=dict(color='white'),
        tickfont=dict(color='white'),
        gridcolor='lightgray'
    ),
    yaxis=dict(
        title_font=dict(color='white'),
        tickfont=dict(color='white'),
        gridcolor='lightgray'
    ),
    legend=dict(
        font=dict(color='white'),
        bordercolor='white',
        borderwidth=1
    )
)

# mostra o gráfico interativo na interface web configurado com a largura elástica stretch
st.plotly_chart(fig, width='stretch')

# expansor opcional para exibir a tabela de projeções na interface, igual ao print do terminal
with st.expander("📄 Visualizar Tabela Completa de Projeções What-If (Dados Amazon)"):
    st.dataframe(df_what_if[['Cenário Desconto', 'Categoria', 'Demanda Projetada (Uds)', 'Lucro Estimado ($)']], width='stretch')