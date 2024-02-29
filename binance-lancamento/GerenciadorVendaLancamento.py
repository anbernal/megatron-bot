import json
import logging
import sqlite3
import requests
from decouple import config
from binance.client import Client

from BinanceVendaLancamento import BinanceVendaLancamento


class GerenciadorVendaLancamento:

    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

        with open(self.config_file_path, 'r') as config_file:
            self.config_data = json.load(config_file)

        api_key = self.config_data['BINANCE_API_KEY']
        api_secret = self.config_data['BINANCE_API_SECRET']
        DATABASE_ADDRESS = "db/megatron.db"
        base_url = 'https://api.binance.com/api/v3/ticker/price'

        self.conn = sqlite3.connect(DATABASE_ADDRESS)
        self.binance_api_key = api_key
        self.binance_api_secret = api_secret
        self.binance_api_base_url = base_url
        self.binance_client = Client(api_key, api_secret)

    def verificar_compras_abertas(self):


        logging.basicConfig(filename=self.config_data['filenamelog'], level=getattr(logging, self.config_data['level_log']), format='%(asctime)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
        
        cursor = self.conn.cursor()
        cursor.execute(""" SELECT 
                                c.id, 
                                c.id_moeda, 
                                c.valor_compra, 
                                c.permite_venda,
                                m.desvalorizacao 
                            FROM 
                                compras_lancamento AS c 
                            JOIN 
                                moeda_lancamento AS m ON c.id_moeda = m.id 
                            WHERE 
                                c.status = 'open'
                        """)
        compras_abertas = cursor.fetchall()

        for compra in compras_abertas:
            compra_id, moeda_id, valor_compra, permite_venda, desvalorizacao  = compra
            porcentagem_desvalorizacao = desvalorizacao
            simbolo_moeda = self.obter_simbolo_moeda(moeda_id)
            valor_atual = self.obter_valor_atual(simbolo_moeda)
            maiorAlta = self.get_maior_Alta_historica(simbolo_moeda)

            valorizacao = ((valor_compra - maiorAlta) / valor_compra) * 100

            if valorizacao < porcentagem_desvalorizacao:
                if(permite_venda == 'S'):
                    print("INICIANDO A VENDA ************")
                    self.realizar_venda(compra_id, simbolo_moeda,valor_atual)
                else:
                    print("A PORCENTAGEM TA OK --- MAS A VENDA NAO FOI PERMITIDA ")
            else:
                self.atualizar_valorizacao_no_banco(compra_id,valorizacao,simbolo_moeda)



    def obter_simbolo_moeda(self, moeda_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT nome_moeda FROM moeda_lancamento WHERE id = ?", (moeda_id,))
        simbolo = cursor.fetchone()
        return simbolo[0] if simbolo else None

    def obter_valor_atual(self, simbolo):
        response = requests.get(f"{self.binance_api_base_url}?symbol={simbolo}")
        if response.status_code == 200:
            data = response.json()
            return float(data["price"])
        else:
            raise Exception(f"Failed to fetch current value for {simbolo}")
        
    def get_maior_Alta_historica(self, simbolo):
    # Obtém os dados históricos dos últimos 1000 candles (velas)
        klines = self.binance_client.get_historical_klines(simbolo, Client.KLINE_INTERVAL_1DAY, "1000 days ago UTC")

        highest_high = None
        for kline in klines:
            # O preço mais alto está no quarto elemento de cada kline
            high_price = float(kline[2])
            if highest_high is None or high_price > highest_high:
                highest_high = high_price

        return highest_high

    def realizar_venda(self, compra_id, simbolo_moeda,valor_atual):
        logging.basicConfig(filename=self.config_data['filenamelog'], level=getattr(logging, self.config_data['level_log']), format='%(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        
        vendedorBinance = BinanceVendaLancamento(self.binance_api_key,self.binance_api_secret,self.config_file_path, self.conn)
        vendedorBinance.realizar_venda(compra_id, simbolo_moeda,valor_atual)

    def atualizar_valorizacao_no_banco(self, compra_id, valorizacao, simbolo_moeda):
        try:
            cursor = self.conn.cursor()

            cursor.execute("UPDATE compras_lancamento SET atual_valorizacao = ? WHERE id = ?", (round(valorizacao, 2), compra_id))
            self.conn.commit()

            logging.info(f'Valorização atualizada no banco para a compra {simbolo_moeda} - LUCRO {round(valorizacao, 2)}%.')
        except Exception as e:
            logging.error(f"Erro ao atualizar valorização no banco de dados: {str(e)}")

    def fechar_conexao(self):
        self.conn.close()