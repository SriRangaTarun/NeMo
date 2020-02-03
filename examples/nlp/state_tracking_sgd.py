"""
This code were adapted from 
https://github.com/google-research/google-research/tree/master/schema_guided_dst
"""

import argparse
import math
import os

import numpy as np
import pickle
from pytorch_transformers import BertTokenizer

import nemo
import nemo_nlp
import nemo_nlp.data.datasets.sgd.data_utils as data_utils
import nemo_nlp.data.datasets.sgd.sgd_preprocessing as utils
from nemo_nlp.data.datasets.sgd import tokenization
from nemo_nlp.utils.callbacks.joint_intent_slot import \
    eval_iter_callback, eval_epochs_done_callback
from nemo.utils.lr_policies import get_lr_policy

from nemo_nlp.modules.sgd import sgd_modules, sgd_model

# Parsing arguments
parser = argparse.ArgumentParser(description='Schema_guided_dst')

# BERT based utterance encoder related arguments
parser.add_argument("--bert_ckpt_dir", default=None, type=str,
                    required=True,
                    help="Directory containing pre-trained BERT checkpoint.")
parser.add_argument("--do_lower_case", default=False, type=bool,
                    help="Whether to lower case the input text. Should be True for uncased "
                    "models and False for cased models.")
parser.add_argument("--preserve_unused_tokens", default=False, type=bool,
                    help="If preserve_unused_tokens is True, Wordpiece tokenization will not "
                    "be applied to words in the vocab.")
parser.add_argument("--max_seq_length", default=80, type=int,
                    help="The maximum total input sequence length after WordPiece tokenization. "
                    "Sequences longer than this will be truncated, and sequences shorter "
                    "than this will be padded.")
parser.add_argument("--dropout", default=0.1, type=float,
                    help="Dropout rate for BERT representations.")

# Hyperparameters and optimization related flags.
parser.add_argument("--num_epochs", default=80, type=int,
                    help="Number of epochs for training")
parser.add_argument("--optimizer_kind", default="adam", type=str)
parser.add_argument("--train_batch_size", default=32, type=int,
                    help="Total batch size for training.")
parser.add_argument("--eval_batch_size", default=8, type=int,
                    help="Total batch size for eval.")
parser.add_argument("--predict_batch_size", default=8, type=int,
                    help="Total batch size for predict.")
parser.add_argument("--learning_rate", default=1e-4, type=float, 
                    help="The initial learning rate for Adam.")
parser.add_argument("--lr_policy", default="WarmupAnnealing", type=str)
parser.add_argument("--num_train_epochs", default=80.0, type=int,
                    help="Total number of training epochs to perform.")
parser.add_argument("--lr_warmup_proportion", default=0.1, type=float,
                    help="Proportion of training to perform linear learning rate warmup for. "
                    "E.g., 0.1 = 10% of training.")
parser.add_argument("--save_epoch_freq", default=1, type=int)
parser.add_argument("--save_step_freq", default=250, type=int,
                    help="How often to save the model checkpoint.")
parser.add_argument("--local_rank", default=None, type=int)
parser.add_argument("--amp_opt_level", default="O0",
                    type=str, choices=["O0", "O1", "O2"])
parser.add_argument("--num_gpus", default=1, type=int)

# Input and output paths and other flags.
parser.add_argument("--task_name", default="dstc8_single_domain", type=str,
                    choices=data_utils.FILE_RANGES.keys(),
                    help="The name of the task to train.")
parser.add_argument("--data_dir", type=str, required=True,
                    help="Directory for the downloaded DSTC8 data, which contains the dialogue files"
                    " and schema files of all datasets (eg train, dev)")
parser.add_argument("--run_mode", default="train", type=str,
                    choices=["train", "predict"],
                    help="The mode to run the script in.")
parser.add_argument("--work_dir", type=str, default="output/SGD",
                    help="The output directory where the model checkpoints will be written.")
parser.add_argument("--schema_embedding_dir", type=str, required=True,
                    help="Directory where .npy file for embedding of entities (slots, values,"
                    " intents) in the dataset_split's schema are stored.")
parser.add_argument("--overwrite_schema_emb_file", action="store_true",
                    help="Whether to generate a new Tf.record file saving the dialogue examples.")
parser.add_argument("--dialogues_example_dir", type=str, required=True,
                    help="Directory where preprocessed DSTC8 dialogues are stored.")
parser.add_argument("--overwrite_dial_file", action="store_true",
                    help="Whether to generate a new file saving the dialogue examples.")
parser.add_argument("--shuffle", type=bool, default=False,
                    help="Whether to shuffle training data")
parser.add_argument("--dataset_split", type=str, required=True,
                    choices=["train", "dev", "test"],
                    help="Dataset split for training / prediction.")



args = parser.parse_args()

if not os.path.exists(args.data_dir):
    raise ValueError('Data not found at {args.data_dir}')

task_name = args.task_name
vocab_file = os.path.join(args.bert_ckpt_dir, "vocab.txt")

if not os.path.exists(vocab_file):
    raise ValueError('vocab_file.txt not found at {args.bert_ckpt_dir}')

work_dir = f'{args.work_dir}/{args.task_name.upper()}'
nf = nemo.core.NeuralModuleFactory(backend=nemo.core.Backend.PyTorch,
                                   local_rank=args.local_rank,
                                   optimization_level=args.amp_opt_level,
                                   log_dir=work_dir,
                                   create_tb_writer=True,
                                   files_to_copy=[__file__],
                                   add_time_to_log_dir=True)


bert_init_ckpt = os.path.join(args.bert_ckpt_dir, "bert_model.ckpt")

pretrained_bert_model = nemo_nlp.huggingface.BERT(
    pretrained_model_name="bert-base-cased", factory=nf)
# hidden_size = pretrained_bert_model.local_parameters["hidden_size"]

tokenization.validate_case_matches_checkpoint(
  do_lower_case=args.do_lower_case, init_checkpoint=bert_init_ckpt)

# BERT tokenizer
tokenizer = tokenization.FullTokenizer(
    vocab_file=vocab_file,
    do_lower_case=args.do_lower_case,
    preserve_unused_tokens=args.preserve_unused_tokens)

# Run SGD preprocessor to generate and store schema embeddings
schema_preprocessor = utils.SchemaPreprocessor(
    data_dir=args.data_dir,
    schema_embedding_dir=args.schema_embedding_dir,
    max_seq_length=args.max_seq_length,
    tokenizer=tokenizer,
    bert_model=pretrained_bert_model,
    dataset_split=args.dataset_split,
    overwrite_schema_emb_file=args.overwrite_schema_emb_file,
    bert_ckpt_dir=args.bert_ckpt_dir,
    nf=nf)

train_datalayer = nemo_nlp.SGDDataLayer(
    task_name=args.task_name,
    vocab_file=vocab_file,
    do_lower_case=args.do_lower_case,
    tokenizer=tokenizer,
    max_seq_length=args.max_seq_length,
    data_dir=args.data_dir,
    dialogues_example_dir=args.dialogues_example_dir,
    overwrite_dial_file=args.overwrite_dial_file,
    shuffle=args.shuffle,
    dataset_split=args.dataset_split,
    schema_emb_processor=schema_preprocessor,
    batch_size=args.train_batch_size)


# fix
bert_config = os.path.join(args.bert_ckpt_dir, 'bert_config.json')
if not os.path.exists(bert_config):
    raise ValueError(f'bert_config.json not found at {args.bert_ckpt_dir}')

input_data = train_datalayer()

hidden_size = pretrained_bert_model.local_parameters["hidden_size"]

# define model pipeline
encoder_extractor = sgd_modules.Encoder(hidden_size=hidden_size,
                                        dropout=args.dropout)
dst_loss = nemo_nlp.SGDDialogueStateLoss()


# Encode the utterances using BERT.
token_embeddings = pretrained_bert_model(input_ids=input_data.utterance_ids,
                                         attention_mask=input_data.utterance_mask,
                                         token_type_ids=input_data.utterance_segment)
encoded_utterance = encoder_extractor(hidden_states=token_embeddings)
model = sgd_model.SGDModel(embedding_dim=hidden_size)

logit_intent_status,\
logit_req_slot_status,\
logit_cat_slot_status,\
logit_cat_slot_value,\
logit_noncat_slot_status,\
logit_noncat_slot_start,\
logit_noncat_slot_end = model(encoded_utterance=encoded_utterance,
                        token_embeddings=token_embeddings,
                        utterance_mask=input_data.utterance_mask,
                        num_categorical_slot_values=input_data.num_categorical_slot_values,
                        num_intents=input_data.num_intents,
                        cat_slot_emb=input_data.cat_slot_emb,
                        cat_slot_value_emb=input_data.cat_slot_value_emb,
                        noncat_slot_emb=input_data.noncat_slot_emb,
                        req_slot_emb=input_data.req_slot_emb,
                        intent_embeddings=input_data.intent_emb)

loss = dst_loss(logit_intent_status=logit_intent_status,
                logit_req_slot_status=logit_req_slot_status,
                logit_cat_slot_status=logit_cat_slot_status,
                logit_cat_slot_value=logit_cat_slot_value,
                logit_noncat_slot_status=logit_noncat_slot_status,
                logit_noncat_slot_start=logit_noncat_slot_start,
                logit_noncat_slot_end=logit_noncat_slot_end,
                intent_status=input_data.intent_status,
                requested_slot_status=input_data.requested_slot_status,
                num_slots=input_data.num_slots,
                categorical_slot_status=input_data.categorical_slot_status,
                num_categorical_slots=input_data.num_categorical_slots,
                categorical_slot_values=input_data.categorical_slot_values,
                noncategorical_slot_status=input_data.noncategorical_slot_status,
                num_noncategorical_slots=input_data.num_noncategorical_slots,
                noncategorical_slot_value_start=input_data.noncategorical_slot_value_start,
                noncategorical_slot_value_end=input_data.noncategorical_slot_value_end)



# eval_datalayer = nemo_nlp.SGDDataLayer(
#     task_name=args.task_name,
#     vocab_file=vocab_file,
#     do_lower_case=args.do_lower_case,
#     tokenizer=tokenizer,
#     max_seq_length=args.max_seq_length,
#     data_dir=args.data_dir,
#     dialogues_example_dir=args.dialogues_example_dir,
#     overwrite_dial_file=args.overwrite_dial_file,
#     shuffle=args.shuffle,
#     dataset_split=args.dataset_split,
#     schema_emb_processor=schema_preprocessor,
#     batch_size=args.train_batch_size)

train_tensors = [loss]
# eval_tensors = [logit_intent_status,
#                 logit_req_slot_status,
#                 logit_cat_slot_status,
#                 logit_cat_slot_value,
#                 logit_noncat_slot_status,
#                 logit_noncat_slot_start,
#                 logit_noncat_slot_end,
#                 input_data.intent_status,
#                 requested_slot_status=input_data.requested_slot_status,
#                 num_slots=input_data.num_slots,
#                 categorical_slot_status=input_data.categorical_slot_status,
#                 num_categorical_slots=input_data.num_categorical_slots,
#                 categorical_slot_values=input_data.categorical_slot_values,
#                 noncategorical_slot_status=input_data.noncategorical_slot_status,
#                 num_noncategorical_slots=input_data.num_noncategorical_slots,
#                 noncategorical_slot_value_start=input_data.noncategorical_slot_value_start,
#                 noncategorical_slot_value_end=input_data.noncategorical_slot_value_end]

steps_per_epoch = len(train_datalayer) // (args.train_batch_size * args.num_gpus)

# import pdb; pdb.set_trace()
# Create trainer and execute training action
train_callback = nemo.core.SimpleLossLoggerCallback(
    tensors=train_tensors,
    print_func=lambda x: print("Loss: {:.3f}".format(x[0].item())),
    get_tb_values=lambda x: [["loss", x[0]]],
    tb_writer=nf.tb_writer)

# eval_callback = nemo.core.EvaluatorCallback(
#     eval_tensors=eval_tensors,
#     user_iter_callback=lambda x, y: eval_iter_callback(x, y),
#     user_epochs_done_callback=lambda x:
#         eval_epochs_done_callback(x, label_ids, f'{nf.work_dir}/graphs'),
#     tb_writer=nf.tb_writer,
#     eval_step=steps_per_epoch)

ckpt_callback = nemo.core.CheckpointCallback(
    folder=nf.checkpoint_dir,
    epoch_freq=args.save_epoch_freq,
    step_freq=args.save_step_freq)

lr_policy_fn = get_lr_policy(args.lr_policy,
                             total_steps=args.num_epochs * steps_per_epoch,
                             warmup_ratio=args.lr_warmup_proportion)

nf.train(tensors_to_optimize=[loss],
         callbacks=[train_callback, ckpt_callback],
         lr_policy=lr_policy_fn,
         optimizer=args.optimizer_kind,
         optimization_params={"num_epochs": args.num_epochs,
                              "lr": args.learning_rate}
                              )


# encoded_utterance = bert_encoder.get_pooled_output()
# encoded_tokens = bert_encoder.get_sequence_output()

# Apply dropout in training mode.
# encoded_utterance = tf.layers.dropout(
#     encoded_utterance, rate=FLAGS.dropout_rate, training=is_training)
# encoded_tokens = tf.layers.dropout(
#     encoded_tokens, rate=FLAGS.dropout_rate, training=is_training)
# return encoded_utterance, encoded_tokens



# TODO: add max_seq_len checkp
"""
bert_config = modeling.BertConfig.from_json_file(
      os.path.join(FLAGS.bert_ckpt_dir, "bert_config.json"))
  if FLAGS.max_seq_length > bert_config.max_position_embeddings:
    raise ValueError(
        "Cannot use sequence length %d because the BERT model "
        "was only trained up to sequence length %d" %
        (FLAGS.max_seq_length, bert_config.max_position_embeddings))
"""


    

# """ Load the pretrained BERT parameters
# See the list of pretrained models, call:
# nemo_nlp.huggingface.BERT.list_pretrained_models()
# """
# pretrained_bert_model = nemo_nlp.huggingface.BERT(
#   pretrained_model_name=args.pretrained_bert_model, factory=nf)
# hidden_size = pretrained_bert_model.local_parameters["hidden_size"]
# tokenizer = BertTokenizer.from_pretrained(args.pretrained_bert_model)

# task_name = args.task_name.lower()
# if task_name not in sgd_utils.FILE_RANGES:
#   raise ValueError(f'Task not found: {task_name}')

# data_desc = SGDDataset(args.data_dir,
#                                    tokenizer,
#                                    task_name=task_name,
#                                    dataset_split=args.dataset_split,
#                                    do_lower_case=args.do_lower_case,
#                                    dataset_name=args.dataset_name,
#                                    none_slot_label=args.none_slot_label,
#                                    pad_label=args.pad_label,
#                                    max_seq_length=args.max_seq_length)

# # Create sentence classification loss on top
# classifier = nemo_nlp.JointIntentSlotClassifier(
#   hidden_size=hidden_size,
#   num_intents=data_desc.num_intents,
#   num_slots=data_desc.num_slots,
#   dropout=args.fc_dropout)

# loss_fn = nemo_nlp.JointIntentSlotLoss(num_slots=data_desc.num_slots)


# def create_pipeline(num_samples=-1,
#                   batch_size=32,
#                   num_gpus=1,
#                   local_rank=0,
#                   mode='train'):
#   nemo.logging.info(f"Loading {mode} data...")
#   data_file = f'{data_desc.data_dir}/{mode}.tsv'
#   slot_file = f'{data_desc.data_dir}/{mode}_slots.tsv'
#   shuffle = args.shuffle_data if mode == 'train' else False

#   data_layer = nemo_nlp.BertJointIntentSlotDataLayer(
#       input_file=data_file,
#       slot_file=slot_file,
#       pad_label=data_desc.pad_label,
#       tokenizer=tokenizer,
#       max_seq_length=args.max_seq_length,
#       num_samples=num_samples,
#       shuffle=shuffle,
#       batch_size=batch_size,
#       num_workers=0,
#       local_rank=local_rank,
#       ignore_extra_tokens=args.ignore_extra_tokens,
#       ignore_start_end=args.ignore_start_end
#   )

#   ids, type_ids, input_mask, loss_mask, \
#   subtokens_mask, intents, slots = data_layer()
#   data_size = len(data_layer)

#   if data_size < batch_size:
#       nemo.logging.warning("Batch_size is larger than the dataset size")
#       nemo.logging.warning("Reducing batch_size to dataset size")
#       batch_size = data_size

#   steps_per_epoch = math.ceil(data_size / (batch_size * num_gpus))
#   nemo.logging.info(f"Steps_per_epoch = {steps_per_epoch}")

#   hidden_states = pretrained_bert_model(input_ids=ids,
#                                         token_type_ids=type_ids,
#                                         attention_mask=input_mask)

#   intent_logits, slot_logits = classifier(hidden_states=hidden_states)

#   loss = loss_fn(intent_logits=intent_logits,
#                  slot_logits=slot_logits,
#                  loss_mask=loss_mask,
#                  intents=intents,
#                  slots=slots)

#   if mode == 'train':
#       tensors_to_evaluate = [loss, intent_logits, slot_logits]
#   else:
#       tensors_to_evaluate = [intent_logits, slot_logits, intents,
#                              slots, subtokens_mask]

#   return tensors_to_evaluate, loss, steps_per_epoch, data_layer


# train_tensors, train_loss, steps_per_epoch, _ = create_pipeline(
#   args.num_train_samples,
#   batch_size=args.batch_size,
#   num_gpus=args.num_gpus,
#   local_rank=args.local_rank,
#   mode=args.train_file_prefix)
# eval_tensors, _, _, data_layer = create_pipeline(
#   args.num_eval_samples,
#   batch_size=args.batch_size,
#   num_gpus=args.num_gpus,
#   local_rank=args.local_rank,
#   mode=args.eval_file_prefix)

# # Create callbacks for train and eval modes
# train_callback = nemo.core.SimpleLossLoggerCallback(
#   tensors=train_tensors,
#   print_func=lambda x: str(np.round(x[0].item(), 3)),
#   tb_writer=nf.tb_writer,
#   get_tb_values=lambda x: [["loss", x[0]]],
#   step_freq=steps_per_epoch)

# eval_callback = nemo.core.EvaluatorCallback(
#   eval_tensors=eval_tensors,
#   user_iter_callback=lambda x, y: eval_iter_callback(
#       x, y, data_layer),
#   user_epochs_done_callback=lambda x: eval_epochs_done_callback(
#       x, f'{nf.work_dir}/graphs'),
#   tb_writer=nf.tb_writer,
#   eval_step=steps_per_epoch)

# # Create callback to save checkpoints
# ckpt_callback = nemo.core.CheckpointCallback(
#   folder=nf.checkpoint_dir,
#   epoch_freq=args.save_epoch_freq,
#   step_freq=args.save_step_freq)

# lr_policy_fn = get_lr_policy(args.lr_policy,
#                            total_steps=args.num_epochs * steps_per_epoch,
#                            warmup_ratio=args.lr_warmup_proportion)

# nf.train(tensors_to_optimize=[train_loss],
#        callbacks=[train_callback, eval_callback, ckpt_callback],
#        lr_policy=lr_policy_fn,
#        optimizer=args.optimizer_kind,
#        optimization_params={"num_epochs": args.num_epochs,
#                             "lr": args.lr,
#                             "weight_decay": args.weight_decay})