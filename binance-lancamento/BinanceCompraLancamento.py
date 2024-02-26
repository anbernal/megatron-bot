import json
import logging
import sqlite3
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime

from BotTelegram import BotTelegram

class BinanceCompraLancamento:
    def __init__(self, api_key, api_secret, database_name, config_file_path):
        self.client = Client(api_key, api_secret)
        self.conn = sqlite3.connect(database_name)
        self.c = self.conn.cursor()
        self.config_file_path = config_file_path

    def comprar(self, nome_moeda):
        with open(self.config_file_path, 'r') as config_file:
            config_data = json.load(config_file)
        
        chat_id = config_data['GRUPO_COMPRA_VENDA']

        # Configurar o logger com base nas configurações do JSON
        logging.basicConfig(filename=config_data['filenamelog'], level=getattr(logging, config_data['level_log']),
                            format='%(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')  # %d/%m/%Y %H:%M:%S

        data_compra = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        parse_mode='markdown'

        try:
            # Recuperado banco de dados o id da moeda
            self.c.execute(
                "SELECT id, valor_entrada_dollar FROM moeda_lancamento WHERE nome_moeda = ?", (nome_moeda,))
            row = self.c.fetchone()

            if row:
                moeda_id = row[0]  # atribui o valor do primeiro campo (id) à variável moeda_id
                valor_entrada_dollar = row[1]  

                # Verifica se já existem registros de compra para a moeda
                self.c.execute(
                    "SELECT COUNT(*) FROM compras_lancamento WHERE id_moeda = (SELECT id FROM moeda_lancamento WHERE nome_moeda = ?) AND status = 'open' ", (nome_moeda,))
                existem_compras = self.c.fetchone()[0]

                if existem_compras == 0:
                    ticker = self.client.get_symbol_ticker(symbol=nome_moeda)
                    preco_atual = float(ticker['price'])
                    quantidade_moedas = valor_entrada_dollar / preco_atual
                    status_compra = 'open'

                    self.c.execute('''INSERT INTO compras_lancamento (id_moeda, data_compra, quantidade, valor_compra, status)
                                    VALUES (?, ?, ?, ?, ?)''', (moeda_id, data_compra, quantidade_moedas, preco_atual, status_compra))
                    self.conn.commit()

                    retornoCompra = self.client.create_order(
                        symbol=nome_moeda,
                        side=Client.SIDE_BUY,
                        type=Client.ORDER_TYPE_MARKET,
                        quoteOrderQty=valor_entrada_dollar
                    )
                    
                    mensagem = (f"\n\n   🚨 *ALERTA COMPRA* 🚨   \n\n Moeda: {nome_moeda}\n\n")
                    botTelegran = BotTelegram('config.json')
                    botTelegran.enviar_mensagem(chat_id,mensagem,parse_mode)
                    
                    logging.info(f'ALERTA A {nome_moeda} comprada com sucesso! ;)  { retornoCompra}')
    
                    return
                else:
                    logging.info(f'A {nome_moeda} não foi comprada já consta na carteira!')
            else:
                logging.info(f'A {nome_moeda} esta com dados nulos')
                pass

        except BinanceAPIException as e:
                logging.error(f'Erro ao fazer a compra: {e}')
