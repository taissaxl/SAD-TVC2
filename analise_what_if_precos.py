import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# PASSO 1: CARREGAR OS DADOS REAIS DO TEU CSV (basket_details.csv)
# =====================================================================
print("A carregar os dados do basket_details.csv...")
try:
    df_real = pd.read_csv('basket_details.csv')
    print("Ficheiro transacional carregado com sucesso!")
except FileNotFoundError:
    print("ERRO: O ficheiro 'basket_details.csv' não foi encontrado.")
    print("Confirma se abriste a PASTA CORRETA no VS Code (File -> Open Folder).")
    exit()

# Como a base transacional tem muitos IDs de produtos e não tem categorias textuais,
# vamos agrupar os produtos pelo último dígito do seu ID para criar 3 Categoria Analíticas válidas.
def categorizar_por_id(pid):
    digito = pid % 3
    if digito == 0: return 'Grupo Eletrónicos'
    elif digito == 1: return 'Grupo Vestuário'
    else: return 'Grupo Beleza & Saúde'

df_real['Categoria'] = df_real['product_id'].apply(categorizar_por_id)

# Agrupamos para extrair a quantidade total real vendida na tua base (basket_count)
df_base = df_real.groupby('Categoria').agg(
    Quantidade_Base=('basket_count', 'sum')
).reset_index()

# Atribuímos preços originais médios condizentes com os grupos para criar o cenário baseline
precos_simulados = {
    'Grupo Eletrónicos': 180.00,
    'Grupo Vestuário': 45.00,
    'Grupo Beleza & Saúde': 25.00
}
df_base['Preco_Original'] = df_base['Categoria'].map(precos_simulados)

# =====================================================================
# PASSO 2: DEFINIR AS PREMISSAS DO TEU SAD (Margens e Elasticidades)
# =====================================================================
# Conforme o referencial teórico de SAD, inserimos as variáveis organizacionais:
df_base['Margem_Lucro_Base'] = [0.40, 0.50, 0.35]   # Margens de 40%, 50% e 35%
df_base['Elasticidade_Demanda'] = [-2.4, -1.4, -0.6] # Eletrónicos (elástico), Vestuário (médio), Beleza (inelástico)

# Calcula o custo unitário fixo de aquisição/produção
df_base['Custo_Unitario'] = df_base['Preco_Original'] * (1 - df_base['Margem_Lucro_Base'])

# =====================================================================
# PASSO 3: MOTOR ANALÍTICO WHAT-IF (Simulação de Cenários)
# =====================================================================
politicas_desconto = [0.00, 0.05, 0.10, 0.15, 0.20] # Cenários de desconto (0% a 20%)
resultados_simulacao = []

for dct in politicas_desconto:
    for idx, row in df_base.iterrows():
        cat = row['Categoria']
        p0 = row['Preco_Original']
        q0 = row['Quantidade_Base']
        custo = row['Custo_Unitario']
        eps = row['Elasticidade_Demanda']
        
        # Projeções matemáticas baseadas na elasticidade-preço da demanda
        p_novo = p0 * (1 - dct)
        q_nova = int(q0 * (1 - (eps * dct)))
        receita_nova = p_novo * q_nova
        lucro_novo = (p_novo - custo) * q_nova
        
        resultados_simulacao.append({
            'Cenário Desconto': f"{int(dct*100)}%",
            'Categoria': cat,
            'Preço Simulado ($)': round(p_novo, 2),
            'Demanda Projetada (Uds)': q_nova,
            'Lucro Estimado ($)': round(lucro_novo, 2)
        })

df_what_if = pd.DataFrame(resultados_simulacao)

# Exibe os resultados no terminal do VS Code
print("\n" + "="*60)
print("             TABELA DE PROJEÇÕES WHAT-IF")
print("="*60)
print(df_what_if.to_string(index=False))
print("="*60 + "\n")

# =====================================================================
# PASSO 4: LÓGICA DE RECOMENDAÇÃO (Tomada de Decisão Automatizada)
# =====================================================================
lucro_por_cenario = df_what_if.groupby('Cenário Desconto')['Lucro Estimado ($)'].sum()
melhor_cenario = lucro_por_cenario.idxmax()
maior_lucro = lucro_por_cenario.max()

print(f"[SISTEMA DE APOIO À DECISÃO - RECOMENDAÇÃO]:")
print(f"O cenário ideal determinado pelo modelo foi a política de {melhor_cenario} de desconto.")
print(f"Esta escolha otimiza as curvas de elasticidade e projeta um Lucro Consolidado de $ {maior_lucro:,.2f}.\n")

# =====================================================================
# PASSO 5: VISUALIZAÇÃO DE DADOS (Geração de Gráfico)
# =====================================================================
plt.figure(figsize=(10, 6))
for cat in df_base['Categoria']:
    dados_cat = df_what_if[df_what_if['Categoria'] == cat]
    plt.plot(dados_cat['Cenário Desconto'], dados_cat['Lucro Estimado ($)'], marker='o', linewidth=2, label=cat)

plt.title('Impacto das Políticas de Desconto no Lucro Líquido (Análise What-If)', fontsize=12, fontweight='bold')
plt.xlabel('Cenários de Desconto Concedido', fontsize=10)
plt.ylabel('Lucro Líquido Total Estimado ($)', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()

# Guarda a imagem na mesma pasta para usares no relatório SBC
plt.savefig('grafico_what_if_basket.png', dpi=300)
print("Gráfico 'grafico_what_if_basket.png' gerado e guardado com sucesso!")
plt.show()