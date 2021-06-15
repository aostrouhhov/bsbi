import os
import sys
import string
from collections import OrderedDict
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import spacy
import pickle

nltk.download('punkt')
nltk.download('stopwords')


# Построение индекса методом BSBI
class BSBI:
    def __init__(self, dir_name, block_size):
        self.block_size = block_size
        self.dir_name = dir_name
        self.number_of_docs = 0
        self.total_docs_size = 0
        self.docID_doc_map = {}
        self.termID_term_map = {}
        self.docID_terms_map = {}

    def build_index(self):
        # Подготовить папку с блоками
        if os.path.exists('blocks'):
            if not os.path.isdir('blocks'):
                os.remove('blocks')
                os.mkdir('blocks')
            else:
                for current_dir, subdirs, files in os.walk('blocks'):
                    for f in files:
                        file_path = os.path.join(current_dir, f)
                        os.remove(file_path)
        else:
            os.mkdir('blocks')

        # Проход по всем документам и задание каждому документу doc_id
        doc_id = 0
        for current_dir, subdirs, files in os.walk(self.dir_name):
            for file in files:
                file_path = os.path.join(current_dir, file)
                self.docID_doc_map[doc_id] = file_path

                # Размер файла в Байтах
                doc_size = os.path.getsize(file_path)
                # Проверим, что каждый файл вмещается в размер блока
                if doc_size >= self.block_size:
                    print('ERROR: {} size is {} KB and it exceeds block size {} KB'.format(
                        self.docID_doc_map[doc_id],
                        doc_size / 1024,
                        self.block_size / 1024))
                    sys.exit(1)
                self.total_docs_size += doc_size
                doc_id += 1

        self.number_of_docs = len(self.docID_doc_map)

        print('Total number of docs: {}'.format(self.number_of_docs))
        print('Total size of docs: {} KB'.format(self.total_docs_size / 1024))

        # Поехали BSBI...
        current_block_id = 0
        current_doc_id = 0
        pairs = []
        term_doc_ids_map = OrderedDict()

        while current_doc_id <= self.total_docs_size - 1:
            print('Current block: {}. Current doc ID: {}.'.format(current_block_id, current_doc_id))

            # Открываем файл как строку байтов
            current_doc_path = self.docID_doc_map[current_doc_id]
            current_file = open(current_doc_path, 'rt', encoding='utf-8')
            text = current_file.read()
            current_file.close()

            # Токенизация - выделить токены
            tokens = word_tokenize(text)
            # Преобразовать в нижний регистр
            tokens = [word.lower() for word in tokens]
            # Убрать пунктуацию с каждого токена
            table = str.maketrans('', '', string.punctuation)
            tokens = [word.translate(table) for word in tokens]
            # Убрать не алфавитные токены
            # Отфильтровать "стоп слова" (распространенные слова - I, We, He, for, off, just и т.д.)
            stop_words = set(stopwords.words("english"))
            tokens = [word for word in tokens if (word.isalpha() and word not in stop_words)]

            # Лемматизация - приведение к нормальной форме
            terms = []
            nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
            doc = spacy.tokens.Doc(nlp.vocab, words=tokens)
            for token in doc:
                if token.lang_ == 'en':
                    terms.append(token.lemma_)

            # Получился список термов для документа: [doc] -> [term1, term2]

            # Записываем в список пары вида (term1, doc1), (term2, doc1), (term3, doc1), ...
            for term in terms:
                pairs.append((term, current_doc_id))

            # Проверка на размер или конец документов.
            # Если достигли размера блока или документы закончились, то:
            # 1) Сортируем
            # 2) Преобразуем в постинги вида [term] -> [doc1, doc2, doc3]
            # 3) Записываем постинги на диск

            current_block_size = sys.getsizeof(pairs)

            if current_doc_id == self.number_of_docs - 1 or current_block_size >= self.block_size:
                print('Sorting')

                # Нас не интересует частота вхождения терма в документ, следовательно,
                # удаляем дубликаты:
                pairs = [t for t in (set(tuple(i) for i in pairs))]
                pairs.sort()

                print('Merging tuples into postings')
                for (term, doc_id) in pairs:
                    if term not in term_doc_ids_map:
                        term_doc_ids_map[term] = []
                    term_doc_ids_map[term].append(doc_id)

                print('Writing block #{} to disk\n'.format(current_block_id))

                # Запись блока на диск
                with open('blocks/block_{}.txt'.format(current_block_id), 'wt', encoding='utf-8') as f:
                    # Пишем построчно каждый постинг в блок диска
                    for term, docIDs in term_doc_ids_map.items():
                        f.write('{} -> {}\n'.format(term, docIDs))

                # Определяемся, остались ли еще файлы
                if not current_doc_id == self.number_of_docs - 1:
                    current_block_id += 1
                    pairs = []
                    term_doc_ids_map = OrderedDict()

                else:
                    # Все документ были обработаны, можно делать merge блоков
                    break

            current_doc_id += 1

        # Делаем слияние блоков
        print('Merging all blocks')
        final_block = open('final_block.txt', 'wt', encoding='utf-8')
        # Открываем все блоки на чтение
        block_files = []  # список блоков
        j = 0  # ИД блока

        for dirpath, _, filenames in os.walk('blocks'):
            for _ in filenames:
                fp = os.path.join(dirpath, 'block_{}.txt'.format(j))
                block_files.append(fp)
                j += 1
        block_files.sort()

        blocks = []
        for file in block_files:
            blocks.append(open(file, 'rt', encoding='utf-8'))

        block_lines = {}
        first_iter = True
        term_to_write = ""

        while True:
            postings = []
            terms = []

            # Читаем из каждого подходящего на чтение блока по строке
            for block in blocks:
                skip_this_block = False

                if first_iter:
                    line = block.readline()
                    block_lines[block] = line
                else:
                    # Если мы записали терм этого блока в финальный индекс, то идем по этому блоку дальше
                    if block_lines[block].split(' -> ')[0] == term_to_write:
                        line = block.readline()
                        block_lines[block] = line

                        # Если прочитали блок до конца
                        if line == '' or line is None:
                            # Убираем его из списка блоков
                            blocks.remove(block)
                            # Удаляем из словаря
                            del block_lines[block]
                            skip_this_block = True
                    # Если в этом блоке смотрим на терм, отличающийся от записанного
                    # в финальный индекс, то не продвигаемся вперед по блоку
                    else:
                        line = block_lines[block]

                if not skip_this_block:
                    postings.append(line)
                    terms.append(line.split(' -> ')[0])

            if len(terms) == 0:
                break

            first_iter = False
            # Берем наименьший терм. Если есть равные ему, то конкатенируем их списки doc_id.
            term_to_write = min(terms)

            final_docs = []

            for posting in postings:
                term = posting.split(' -> ')[0]

                if term == term_to_write:
                    docs = []
                    for doc_id in list(posting.split(' -> ')[1][1:-2].split(', ')):
                        docs.append(doc_id)
                    final_docs = final_docs + docs

            final_posting = term_to_write + ' -> ' + str(final_docs)

            # Записываем постинг в финальный блок.
            final_block.write(final_posting + '\n')

        print("Done!")
        print('Size of final_block: {} KB'.format(os.path.getsize('final_block.txt') / 1024))

        # Запишем в pickle файл структуру, которая отображает doc_id в имя документа
        # Будем использоавть это в find.py
        with open('docID_doc_map.pickle', 'wb') as f:
            pickle.dump(self.docID_doc_map, f)
