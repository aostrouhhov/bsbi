import os
import sys
import string
from collections import OrderedDict
from collections import deque

import nltk
nltk.download('punkt')
nltk.download('stopwords')
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

import spacy

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

        # Проход по всем документам и задание каждому документу docID
        docID = 0
        for current_dir, subdirs, files in os.walk(self.dir_name):
            for file in files:
                file_path = os.path.join(current_dir, file)
                self.docID_doc_map[docID] = file_path

                # Размер файла в Байтах
                doc_size = os.path.getsize(file_path)
                # Проверим, что каждый файл вмещается в размер блока
                if doc_size >= self.block_size:
                    print('ERROR: {} size is {} KB and it exceeds block size {} KB'.format(
                        self.docID_doc_map[docID],
                        doc_size / 1024,
                        self.block_size / 1024))
                    sys.exit(1)
                self.total_docs_size += doc_size
                docID += 1

        self.number_of_docs = len(self.docID_doc_map)

        print('Total number of docs: {}'.format(self.number_of_docs))
        print('Total size of docs: {} KB'.format(self.total_docs_size / 1024))

        # Поехали...
        current_blockID = 0
        current_docID = 0
        pairs = []
        term_docIds_map = OrderedDict()

        while (current_docID <= self.total_docs_size - 1):
            print('Current block: {}. Current doc ID: {}.'.format(current_blockID, current_docID))

            # Открываем файл как строку байтов
            current_doc_path = self.docID_doc_map[current_docID]
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
            tokens = [word for word in tokens if word.isalpha()]
            # Отфильтровать "стоп слова" (распространенные слова - I, We, He, for, off, just и т.д.)
            stop_words = set(stopwords.words("english"))
            tokens = [word for word in tokens if not word in stop_words]

            # Лемматизация - приведение к нормальной форме
            terms = []
            nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
            doc = spacy.tokens.Doc(nlp.vocab, words=tokens)
            for token in doc:
                if token.lang_ == "en":
                    terms.append(token.lemma_)

            # Получился список термов для документа: [doc] -> [term1, term2]

            # Записываем в список пары вида (term1, doc1), (term2, doc1), (term3, doc1), ...
            for term in terms:
                pairs.append((term, current_docID))

            # Проверка на размер или конец документов.
            # Если достигли размера блока или документы закончились, то:
            # 1) Сортируем
            # 2) Преобразуем в постинги вида [term] -> [doc1, doc2, doc3]
            # 3) Записываем постинги на диск

            current_block_size = sys.getsizeof(pairs)

            if current_docID == self.number_of_docs - 1 or current_block_size >= self.block_size:
                print('Sorting')

                # ПОКА нас не интересует частота вхождения терма в документ, следовательно,
                # удаляем дубликаты:
                pairs = [t for t in (set(tuple(i) for i in pairs))]
                pairs.sort()

                print('Merging tuples into postings')
                for (term, docID) in pairs:
                    if term not in term_docIds_map:
                        term_docIds_map[term] = []
                    term_docIds_map[term].append(docID)

                print('Writing block #{} to disk\n'.format(current_blockID))

                # Запись блока на диск
                with open('blocks/block_{}.txt'.format(current_blockID), 'wt', encoding='utf-8') as f:
                    # Пишем построчно каждый постинг в блок диска
                    for term, docIDs in term_docIds_map.items():
                        f.write('{} -> {}\n'.format(term, docIDs))

                # Определяемся, остались ли еще файлы
                if not current_docID == self.number_of_docs - 1:
                    current_blockID += 1
                    pairs = []
                    term_docIds_map = OrderedDict()

                else:
                    # Все документ были обработаны, можно делать merge блоков
                    break

            current_docID += 1

        # Делаем слияние блоков
        print('Merging')
        block_queue = deque()
        i = 0 # ИД блока слияния
        j = 0 # ИД обычного блока

        # Заталкиваем в очередь все блоки
        for dirpath, _, filenames in os.walk('blocks'):
            for file in filenames:
                fp = os.path.join(dirpath, 'block_{}.txt'.format(j))
                block_queue.append(fp)
                j+=1

        # Пока очередь не опустела, продолжаем слияние
        while len(block_queue) > 1:
            # Берем очередные блоки
            block_a_file = block_queue.popleft()
            block_b_file = block_queue.popleft()

            # Открываем
            block_a = open(block_a_file, 'rt', encoding='utf-8')
            block_b = open(block_b_file, 'rt', encoding='utf-8')

            # Читаем построчно, целиком не выйдет - не влезут в память
            posting_from_a = block_a.readline()  # Постинг из блока А
            posting_from_b = block_b.readline()  # Постинг из блока Б

            # Результаты слияния
            merged_path = os.path.join('blocks/', 'merged_{}.txt'.format(i))
            file_merged = open(merged_path, 'wt', encoding='utf-8')

            posting_from_a = posting_from_a[:-1].split(' -> ')
            posting_from_b = posting_from_b[:-1].split(' -> ')
            first = True

            while True:
                if posting_from_a[0] == posting_from_b[0]:
                    # Если это один терм
                    term = posting_from_a[0]
                    docs = []
                    for docID in list(posting_from_a[1][1:-1].split(', ')):
                        docs.append(docID)
                    for docID in list(posting_from_b[1][1:-1].split(', ')):
                        docs.append(docID)
                    ptr = None
                    # Конкатенируем докИД-шки
                    file_merged.write(term + ' -> ' + '[' + ", ".join(docs) + ']' + '\n')
                elif posting_from_a[0] < posting_from_b[0]:
                    term = posting_from_a[0]
                    docs = []
                    try:
                        for docID in list(posting_from_a[1][1:-1].split(', ')):
                            docs.append(docID)
                    except:
                        print(posting_from_a)
                    file_merged.write(term + ' -> ' + '[' + ", ".join(docs) + ']' + '\n')
                    # Двигаемся по файлу А
                    ptr = block_a
                elif posting_from_a[0] > posting_from_b[0]:
                    term = posting_from_b[0]
                    docs = []
                    for docID in list(posting_from_b[1][1:-1].split(', ')):
                        docs.append(docID)
                    file_merged.write(term + ' -> ' + '[' + ", ".join(docs) + ']' + '\n')
                    # Двигаемся по файлу Б
                    ptr = block_b

                if ptr == block_a:
                    posting_from_a = block_a.readline()
                    if posting_from_a == '':
                        break
                    posting_from_a = posting_from_a[:-1].split(' -> ')
                elif ptr == block_b:
                    posting_from_b = block_b.readline()
                    if posting_from_b == '':
                        break
                    posting_from_b = posting_from_b[:-1].split(' -> ')
                else:
                    posting_from_a = block_a.readline()
                    posting_from_a = posting_from_a[:-1].split(' -> ')
                    posting_from_b = block_b.readline()
                    posting_from_b = posting_from_b[:-1].split(' -> ')

            # Какой-то файл закончился
            if posting_from_a == '':
                ptr = block_b
                block_a.close()
            else:
                ptr = block_a
                block_b.close()

            posting = ptr.readline()

            while posting != '':
                # Записать оставшиеся строки в блок слияния
                posting = posting[:-1].split(' -> ')
                file_merged.write(posting[0] + ' -> ' + posting[1] + '\n')
                posting = ptr.readline()
            ptr.close()
            file_merged.close()
            block_queue.append(merged_path)
            i += 1
