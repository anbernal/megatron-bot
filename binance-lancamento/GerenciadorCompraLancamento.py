import logging
import time
import json

from BinanceCompraLancamento import BinanceCompraLancamento
from BinanceSpotBalance import BinanceSpotBalance, check_balance_min
from GerenciadorMoedas import GerenciadorMoedas
from decouple import config

class GerenciadorCompraLancamento:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

    def run(self):
        with open(self.config_file_path, 'r') as config_file:
            config_data = json.load(config_file)

        api_key = config_data['BINANCE_API_KEY']
        api_secret = config_data['BINANCE_API_SECRET']
        DATABASE_ADDRESS = "db/megatron.db"
        symbol_to_check = config_data['SYMBOL_TO_CHECK']
        minimum_balance = config_data['MINIMUM_BALANCE']

        # Configurar o logger com base nas configurações do JSON
        logging.basicConfig(filename=config_data['filenamelog'], level=getattr(logging, config_data['level_log']), format='%(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')

        gerenciador = GerenciadorMoedas(DATABASE_ADDRESS)

        compradorBinance = BinanceCompraLancamento(api_key, api_secret, DATABASE_ADDRESS, self.config_file_path)
        binance_balance = BinanceSpotBalance(api_key, api_secret)

        while True:
            try:
                moedas = gerenciador.listar_moedas()

                if moedas:
                    for nome_moeda in moedas:
                        #logging.info(f'O MFI para {nome_moeda} -> : {round(mfi_value, 2)}')
                        logging.info(f'A criptomoeda {nome_moeda[0]} está no processo de compra.\n')
                        account_balances = binance_balance.get_balance()
                        balance = check_balance_min(account_balances, symbol_to_check, minimum_balance)

                        if balance >= minimum_balance:
                            compradorBinance.comprar(nome_moeda[0])
                            # logging.info(f"O saldo é  {balance}.\n")
                        else:
                            logging.info(f"O saldo é inferior a $ {minimum_balance} o saldo atual é:{balance}.\n")


                    logging.info("Concluído .....\n")
                else:
                    logging.info("Nenhuma criptomoeda cadastrada.")

                time.sleep(30)
            except Exception as e_outer:
                logging.error(f"Erro durante a execução do loop principal GerenciadorCompra : {e_outer}")