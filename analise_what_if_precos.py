import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("A carregar os dados do amazon.csv...")
try:
    df = pd.read_csv('amazon.csv')
    print("Ficheiro da Amazon carregado com sucesso!")
except FileNotFoundError:
    print("ERRO: O ficheiro 'amazon.csv' não foi encontrado na pasta.")
    exit()

# Limpeza dos dados: remover o símbolo '₹' (Rupia) e converter preços para float
def limpar_preco(valor):
    if pd.isna(valor): return 0.0
    return float(str(valor).replace('₹', '').replace(',', '').strip())

df['Preco_Original'] = df['actual_price'].apply(limpar_preco)

# Como a coluna category tem subcategorias longas separadas por '|',
# vamos extrair apenas o primeiro nome para termos categorias limpas.
df['Categoria_Principal'] = df['category'].apply(lambda x: str(x).split('|')[0] if pd.notna(x) else 'Outros')

# Filtrar o volume de demanda (remover vírgulas do rating_count)
df['Demanda_Base'] = df['rating_count'].astype(str).str.replace(',', '').str.strip()
df['Demanda_Base'] = pd.to_numeric(df['Demanda_Base'], errors='coerce').fillna(100)

# Agrupamos por Categoria Principal para extrair a média de preço real e volume real
df_base = df.groupby('Categoria_Principal').agg(
    Preco_Original=('Preco_Original', 'mean'),
    Quantidade_Base=('Demanda_Base', 'sum')
).reset_index()

# Selecionamos as 3 categorias com maior volume para o estudo ficar focado e limpo
df_base = df_base.sort_values(by='Quantidade_Base', ascending=False).head(3).copy()

# Injetando as variáveis do SAD (Margens e Elasticidades)
# Como a base não traz margem nem elasticidade, o SAD injeta estas premissas:
df_base['Margem_Lucro_Base'] = [0.40, 0.45, 0.35]   # Margens organizacionais simuladas
df_base['Elasticidade_Demanda'] = [-2.5, -1.4, -0.8] # Elasticidades comportamentais simuladas

# Calcula o custo unitário fixo com base nos preços reais extraídos da Amazon
df_base['Custo_Unitario'] = df_base['Preco_Original'] * (1 - df_base['Margem_Lucro_Base'])

# Motor Analítico What-If (Simulação de Cenários)
politicas_desconto = [0.00, 0.05, 0.10, 0.15, 0.20] # Políticas a testar: 0% a 20%
resultados_simulacao = []

for dct in politicas_desconto:
    for idx, row in df_base.iterrows():
        cat = row['Categoria_Principal']
        p0 = row['Preco_Original']
        q0 = row['Quantidade_Base']
        custo = row['Custo_Unitario']
        eps = row['Elasticidade_Demanda']
        
        # Projeções do que aconteceria (What-If)
        p_novo = p0 * (1 - dct)
        q_nova = int(q0 * (1 - (eps * dct))) # Modelo matemático da elasticidade-preço
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

# Exibição dos resultados no terminal
print("\n" + "="*60)
print("             TABELA DE PROJEÇÕES WHAT-IF (DADOS AMAZON)")
print("="*60)
print(df_what_if[['Cenário Desconto', 'Categoria', 'Demanda Projetada (Uds)', 'Lucro Estimado ($)']].to_string(index=False))
print("="*60 + "\n")

# Tomada de decisão automatizada
lucro_por_cenario = df_what_if.groupby('Cenário Desconto')['Lucro Estimado ($)'].sum()
melhor_cenario = lucro_por_cenario.idxmax()
maior_lucro = lucro_por_cenario.max()

print(f"[RECOMENDAÇÃO AUTOMÁTICA DO SAD]:")
print(f"O cenário ideal para maximizar o retorno é a política de {melhor_cenario} de desconto.")
print(f"Lucro Consolidado Projetado: $ {maior_lucro:,.2f}\n")

# Visualização dos dados
plt.figure(figsize=(10, 6))
for cat in df_base['Categoria_Principal']:
    dados_cat = df_what_if[df_what_if['Categoria'] == cat]
    plt.plot(dados_cat['Cenário Desconto'], dados_cat['Lucro Estimado ($)'], marker='o', linewidth=2, label=cat)

plt.title('Análise What-If: Impacto dos Descontos no Lucro (Base Amazon)', fontsize=12, fontweight='bold')
plt.xlabel('Cenários de Desconto Concedido')
plt.ylabel('Lucro Líquido Projetado ($)')
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.savefig('grafico_what_if_amazon.png', dpi=300)
print("Gráfico 'grafico_what_if_amazon.png' guardado!")
plt.show()